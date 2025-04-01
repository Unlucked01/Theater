#!/usr/bin/perl
use strict;
use warnings;
use utf8;
use CGI::Simple;
use DBI;
use Template;
use DateTime;
use File::Spec;
use MIME::Base64;
use FindBin;
use lib "$FindBin::Bin/..";
use open ':std', ':encoding(UTF-8)';
use Encode;
use JSON::PP;
use CGI::Carp qw(fatalsToBrowser);
use HTML::Template;

# Устанавливаем флаги для корректной обработки UTF-8
binmode(STDIN, ':utf8');
binmode(STDOUT, ':utf8');
binmode(STDERR, ':utf8');

# Set the default encoding for JSON::PP to UTF-8
my $json = JSON::PP->new->utf8(1);

# Инициализация CGI
my $cgi = CGI::Simple->new;
$CGI::Simple::DISABLE_UPLOADS = 0;
$CGI::Simple::POST_MAX = 1024 * 1024;

# Set the default encoding for CGI::Simple
$CGI::Simple::HEADERS{'charset'} = 'utf-8';

# Маршрутизация
my $action = $cgi->url_param('action') || $cgi->param('action') || 'home';

# Отладочная информация
warn "Request method: " . $cgi->request_method();
warn "URL action param: " . ($cgi->url_param('action') || 'none');
warn "POST action param: " . ($cgi->param('action') || 'none');
warn "Final action: " . $action;
warn "Event ID param: " . ($cgi->param('event_id') || 'none');
warn "All params: " . join(", ", $cgi->param());
warn "Raw post data: " . ($cgi->param('POSTDATA') || '');
warn "Content length: " . ($ENV{CONTENT_LENGTH} || 'none');
warn "Content type: " . ($ENV{CONTENT_TYPE} || 'none');
warn "Query string: " . ($ENV{QUERY_STRING} || 'none');
warn "Request URI: " . ($ENV{REQUEST_URI} || 'none');

# Определяем корневую директорию проекта
my $project_root = "$FindBin::Bin/..";

# Подключение к базе данных с поддержкой UTF-8
my $db_file = File::Spec->catfile($project_root, 'database', 'theater.db');

warn "Attempting to connect to database at: $db_file";

my $dbh = DBI->connect("dbi:SQLite:dbname=$db_file", "", "", {
    RaiseError => 1,
    AutoCommit => 1,
    sqlite_unicode => 1,
    sqlite_utf8 => 1
}) or die $DBI::errstr;

warn "Database connected successfully";
$dbh->do("PRAGMA encoding = 'UTF-8'");

# Initialize database if it doesn't exist
unless (-e $db_file) {
    warn "Database file does not exist, initializing...";
    my $init_sql = File::Spec->catfile($project_root, 'database', 'init.sql');
    if (-e $init_sql) {
        warn "Found init.sql at: $init_sql";
        open(my $fh, '<', $init_sql) or die "Cannot open init.sql: $!";
        my $sql = do { local $/; <$fh> };
        close $fh;
        
        # Split SQL statements and execute them one by one
        foreach my $stmt (split /;/, $sql) {
            $stmt =~ s/^\s+|\s+$//g;
            if ($stmt) {
                warn "Executing SQL statement: $stmt";
                eval {
                    $dbh->do($stmt) or warn "Error executing SQL: $DBI::errstr";
                };
                if ($@) {
                    warn "Error executing SQL statement: $@";
                }
            }
        }
        warn "Database initialization completed";
    } else {
        warn "init.sql not found at: $init_sql";
    }
} else {
    warn "Database file already exists at: $db_file";
}

# Verify tables exist
my @tables = qw(users events zones event_zones orders cart);
foreach my $table (@tables) {
    my $sth = $dbh->prepare("SELECT name FROM sqlite_master WHERE type='table' AND name=?");
    $sth->execute($table);
    if ($sth->fetchrow_arrayref) {
        warn "Table '$table' exists";
    } else {
        warn "Table '$table' does not exist!";
    }
}

# Инициализация шаблонизатора с поддержкой UTF-8
my $template = Template->new({
    INCLUDE_PATH => '/usr/local/apache2/htdocs/templates',
    ENCODING => 'utf8',
    UNICODE => 1
});

# Add debug logging for template path
warn "Template include path: /usr/local/apache2/htdocs/templates";
warn "Template files in directory: " . join(", ", glob("/usr/local/apache2/htdocs/templates/*.html"));

# Получение текущего пользователя из сессии
my $current_user = get_current_user();

# Не выводим заголовок для действий, которые сами управляют заголовками
unless ($action eq 'logout' || $action eq 'add_to_cart' || $action eq 'register' || $action eq 'do_login' || 
        $action eq 'update_order_status' || $action eq 'update_user_role') {
    print $cgi->header(-type => 'text/html', -charset => 'utf-8');
}

# Map of actions to handler functions
my %action_handlers = (
    'home' => \&show_home,
    'login' => \&show_login,
    'do_login' => \&handle_login,
    'register' => \&handle_register,
    'logout' => \&handle_logout,
    'admin' => \&show_admin,
    'manager' => \&show_manager,
    'create_event' => \&handle_create_event,
    'events' => \&show_events,
    'event' => \&show_event,
    'cart' => \&show_cart,
    'select_zone' => \&handle_select_zone,
    'add_to_cart' => \&handle_add_to_cart,
    'remove_from_cart' => \&handle_remove_from_cart,
    'checkout' => \&handle_checkout,
    'update_order_status' => \&handle_update_order_status,
    'update_user_role' => \&handle_update_user_role,
    'delete_user' => \&handle_delete_user,
    'add_event' => \&handle_add_event,
);

# Instead, let's create a proper 404 handler
sub show_404 {
    my $vars = {
        title => 'Страница не найдена',
        user => $current_user
    };
    
    print $cgi->header(-status => '404 Not Found', -type => 'text/html', -charset => 'utf-8');
    $template->process('404.html', $vars)
        or die $template->error();
}

# Add a default route for unknown actions
if (exists $action_handlers{$action}) {
    $action_handlers{$action}->();
} else {
    show_404();
}


# Функции для работы с пользователями
sub get_current_user {
    my $user_id = $cgi->cookie('user_id');
    return unless $user_id;

    my $sth = $dbh->prepare("SELECT * FROM users WHERE id = ?");
    $sth->execute($user_id);
    return $sth->fetchrow_hashref;
}

sub authenticate_user {
    my ($login, $password) = @_;
    
    # Отладочная информация
    warn "Trying to authenticate user: $login with password: $password";
    
    my $sth = $dbh->prepare("SELECT * FROM users WHERE login = ? AND password = ?");
    $sth->execute($login, $password);
    my $user = $sth->fetchrow_hashref;
    
    # Отладочная информация
    if ($user) {
        warn "User found: " . $user->{login} . " with role: " . $user->{role};
    } else {
        warn "User not found";
    }
    
    return $user;
}

# Обработчики страниц
sub show_home {
    my $vars = {
        title => 'Главная',
        user => $current_user,
        latest_events => get_latest_events()
    };
    
    $template->process('home.html', $vars)
        or die $template->error();
}

sub show_events {
    my $search = $cgi->param('search');
    my $performers = $cgi->param('performers');
    my $venue = $cgi->param('venue');
    my $status = $cgi->param('status') || '';
    my $date = $cgi->param('date');
    my $time_start = $cgi->param('time_start');
    
    # Декодируем параметры из UTF-8
    $search = Encode::decode_utf8($search) if $search;
    $performers = Encode::decode_utf8($performers) if $performers;
    $venue = Encode::decode_utf8($venue) if $venue;
    
    my $where_clause = "1=1";
    my @bind_values;
    
    if ($search) {
        $where_clause .= " AND title LIKE ?";
        push @bind_values, "%$search%";
    }
    
    if ($performers) {
        $where_clause .= " AND performers LIKE ?";
        push @bind_values, "%$performers%";
    }
    
    if ($venue) {
        $where_clause .= " AND venue LIKE ?";
        push @bind_values, "%$venue%";
    }
    
    if ($status) {
        if ($status eq 'future') {
            $where_clause .= " AND date > date('now')";
        } elsif ($status eq 'today') {
            $where_clause .= " AND date = date('now')";
        } elsif ($status eq 'past') {
            $where_clause .= " AND date < date('now')";
        }
    }
    
    if ($date) {
        $where_clause .= " AND date = ?";
        push @bind_values, $date;
    }
    
    if ($time_start) {
        if ($time_start eq 'morning') {
            $where_clause .= " AND time >= '09:00' AND time < '12:00'";
        } elsif ($time_start eq 'afternoon') {
            $where_clause .= " AND time >= '12:00' AND time < '17:00'";
        } elsif ($time_start eq 'evening') {
            $where_clause .= " AND time >= '17:00' AND time < '23:00'";
        }
    }

    my $events = $dbh->selectall_arrayref(
        "SELECT *, 
         CASE 
             WHEN date < date('now') THEN 'past'
             WHEN date = date('now') THEN 'today'
             ELSE 'future'
         END as event_status
         FROM events 
         WHERE $where_clause
         ORDER BY 
             CASE 
                 WHEN date >= date('now') THEN 0 
                 ELSE 1 
             END,
             date ASC, 
             time ASC",
        { Slice => {} },
        @bind_values
    );

    my $vars = {
        events => $events,
        search => $search,
        performers => $performers,
        venue => $venue,
        selected_date => $date,
        time_start => $time_start,
        status => $status,
        user => $current_user
    };
    
    $template->process('events.html', $vars)
        or die $template->error();
}

sub show_cart {
    unless ($current_user) {
        print $cgi->redirect('?action=login');
        return;
    }
    
    my $vars = {
        title => 'Корзина',
        user => $current_user,
        cart_items => get_cart_items($current_user->{id})
    };
    
    $template->process('cart.html', $vars)
        or die $template->error();
}

sub show_login {
    warn "Entering show_login function";
    
    # Отправляем заголовок с правильной кодировкой
    #print $cgi->header(-type => 'text/html', -charset => 'utf-8');
    warn "Header sent";
    
    my $error = $cgi->param('error');
    my $error_message;
    
    warn "Error parameter: " . ($error || 'none');
    
    if ($error) {
        if ($error eq 'passwords_mismatch') {
            $error_message = 'Пароли не совпадают';
        } elsif ($error eq 'registration_failed') {
            $error_message = 'Ошибка при регистрации. Возможно, такой логин уже занят';
        } elsif ($error eq '1') {
            $error_message = 'Неправильный логин или пароль';
        }
    }
    
    my $vars = {
        title => 'Вход',
        user => $current_user,
        error => $error_message
    };
    
    warn "Template variables prepared: " . $json->encode($vars);
    warn "Template path: " . File::Spec->catdir($project_root, 'templates', 'login.html');
    
    eval {
        $template->process('login.html', $vars)
            or die "Template processing failed: " . $template->error();
        warn "Template processed successfully";
    };
    if ($@) {
        warn "Error processing template: $@";
        die $@;
    }
}

sub show_admin {
    unless ($current_user && $current_user->{role} eq 'admin') {
        print $cgi->redirect('?action=login');
        return;
    }
    
    my $stats = get_sales_statistics();
    
    # Get the tab parameter if provided
    my $active_tab = $cgi->param('tab') || 'dashboard';
    
    my $vars = {
        title => 'Админ-панель',
        user => $current_user,
        users => get_all_users(),
        events => get_all_events(),
        orders => get_all_orders(),
        total_orders => $stats->{total_orders},
        active_orders => $stats->{active_orders},
        total_events => $stats->{total_events},
        event_stats => $stats->{event_stats},
        event_sales_data => $stats->{event_sales_data},
        active_tab => $active_tab
    };
    
    print $cgi->header(-type => 'text/html', -charset => 'utf-8');
    $template->process('admin.html', $vars)
        or die $template->error();
}

sub show_manager {
    unless ($current_user && $current_user->{role} eq 'manager' || $current_user->{role} eq 'admin') {
        print $cgi->redirect('?action=home');
        return;
    }
    
    my $orders = $dbh->selectall_arrayref(
        "SELECT o.*, u.login as user_login, e.title as event_title, e.date as event_date, e.time as event_time, z.name as zone_name 
         FROM orders o 
         JOIN users u ON o.user_id = u.id 
         JOIN events e ON o.event_id = e.id 
         JOIN zones z ON o.zone_id = z.id 
         ORDER BY o.created_at DESC",
        { Slice => {} }
    );
    
    # Get all zones
    my $zones = $dbh->selectall_arrayref(
        "SELECT * FROM zones ORDER BY name",
        { Slice => {} }
    );
    
    my $vars = {
        title => 'Панель менеджера',
        user => $current_user,
        orders => $orders,
        zones => $zones
    };
    
    $template->process('manager.html', $vars)
        or die $template->error();
}

sub show_event {
    my $event_id = $cgi->param('event_id');
    
    # Get event details
    my $event = $dbh->selectrow_hashref(
        "SELECT * FROM events WHERE id = ?",
        undef,
        $event_id
    );
    
    unless ($event) {
        print $cgi->redirect('?action=events');
        return;
    }
    
    # Get zones for this event
    my $event_zones = $dbh->selectall_arrayref(
        "SELECT z.*, ez.available_seats 
         FROM zones z 
         JOIN event_zones ez ON z.id = ez.zone_id 
         WHERE ez.event_id = ?",
        { Slice => {} },
        $event_id
    );
    
    my $vars = {
        title => $event->{title},
        user => $current_user,
        event => $event,
        event_zones => $event_zones
    };
    
    $template->process('event.html', $vars)
        or die $template->error();
}

sub get_sales_statistics {
    # Используем глобальное подключение к БД
    
    # Общее количество заказов
    my $total_orders = $dbh->selectrow_array("SELECT COUNT(*) FROM orders");
    
    # Активные заказы (в статусе "Ожидает" или "Подтвержден")
    my $active_orders = $dbh->selectrow_array("SELECT COUNT(*) FROM orders WHERE status IN ('Ожидает', 'Подтвержден')");
    
    # Общее количество мероприятий
    my $total_events = $dbh->selectrow_array("SELECT COUNT(*) FROM events");
    
    # Статистика продаж по мероприятиям
    my $event_stats = $dbh->selectall_arrayref(
        "SELECT e.id, e.title, COUNT(o.id) as sales 
         FROM events e 
         LEFT JOIN orders o ON e.id = o.event_id 
         GROUP BY e.id, e.title 
         ORDER BY sales DESC 
         LIMIT 10",
        { Slice => {} }
    );
    
    # Вычисляем процент для каждого мероприятия
    my $max_sales = 0;
    foreach my $stat (@$event_stats) {
        $max_sales = $stat->{sales} if $stat->{sales} > $max_sales;
    }
    
    foreach my $stat (@$event_stats) {
        $stat->{percentage} = $max_sales ? int(($stat->{sales} / $max_sales) * 100) : 0;
    }
    
    # Создаем хэш с общими продажами билетов по каждому мероприятию
    my $event_sales_data = {};
    my $sales_by_event = $dbh->selectall_arrayref(
        "SELECT e.id, SUM(o.quantity) as total_tickets
         FROM events e
         LEFT JOIN orders o ON e.id = o.event_id
         GROUP BY e.id",
        { Slice => {} }
    );
    
    foreach my $row (@$sales_by_event) {
        $event_sales_data->{$row->{id}} = $row->{total_tickets} || 0;
    }
    
    return {
        total_orders => $total_orders,
        active_orders => $active_orders,
        total_events => $total_events,
        event_stats => $event_stats,
        event_sales_data => $event_sales_data
    };
}

# Вспомогательные функции
sub get_latest_events {
    my $sth = $dbh->prepare(
        "SELECT * FROM events 
         WHERE date >= date('now') 
         ORDER BY date, time 
         LIMIT 5"
    );
    $sth->execute();
    my $events = $sth->fetchall_arrayref({});
    
    # Ensure UTF-8 encoding for text fields
    foreach my $event (@$events) {
        $event->{title} = $event->{title};
        $event->{performers} = $event->{performers};
        $event->{venue} = $event->{venue};
        $event->{description} = $event->{description};
    }
    
    return $events;
}

sub get_all_events {
    my $sth = $dbh->prepare(
        "SELECT *, 
                CASE 
                    WHEN date < date('now') THEN 'past'
                    WHEN date = date('now') THEN 'today'
                    ELSE 'future'
                END as event_status
         FROM events 
         ORDER BY 
            date >= date('now') DESC,
            date ASC,
            time ASC"
    );
    $sth->execute();
    my $events = $sth->fetchall_arrayref({});
    
    foreach my $event (@$events) {
        $event->{title} = $event->{title};
        $event->{performers} = $event->{performers};
        $event->{venue} = $event->{venue};
        $event->{description} = $event->{description};
    }
    
    return $events;
}

sub get_cart_items {
    my ($user_id) = @_;
    
    my $cart_items = $dbh->selectall_arrayref(
        "SELECT c.id, c.event_id, c.zone_id, c.quantity, c.total_price, c.seat_numbers,
                e.title, e.date, e.time, e.venue,
                z.name AS zone_name, z.price AS zone_price
         FROM cart c
         JOIN events e ON c.event_id = e.id
         JOIN zones z ON c.zone_id = z.id
         WHERE c.user_id = ?",
        { Slice => {} },
        $user_id
    );
    
    return $cart_items;
}

sub get_all_users {
    my $sth = $dbh->prepare("SELECT * FROM users ORDER BY id");
    $sth->execute();
    return $sth->fetchall_arrayref({});
}

sub get_all_orders {
    my $sth = $dbh->prepare(
        "SELECT o.*, u.login as user_login, e.title as event_title, 
         e.date as event_date, e.time as event_time, z.name as zone_name
         FROM orders o
         JOIN users u ON o.user_id = u.id
         JOIN events e ON o.event_id = e.id
         JOIN zones z ON o.zone_id = z.id
         ORDER BY o.created_at DESC"
    );
    $sth->execute();
    return $sth->fetchall_arrayref({});
}

sub get_manager_events {
    my ($user_id) = @_;
    
    my $sth = $dbh->prepare(
        "SELECT * FROM events 
         WHERE date >= date('now') 
         ORDER BY date, time"
    );
    $sth->execute();
    return $sth->fetchall_arrayref({});
}

sub get_manager_orders {
    my ($user_id) = @_;
    
    my $sth = $dbh->prepare(
        "SELECT o.*, u.login as user_login, e.title as event_title,
                e.date as event_date, e.time as event_time,
                z.name as zone_name, z.price as zone_price
         FROM orders o
         JOIN users u ON o.user_id = u.id
         JOIN events e ON o.event_id = e.id
         JOIN zones z ON o.zone_id = z.id
         ORDER BY 
            CASE o.status
                WHEN 'pending' THEN 1
                WHEN 'confirmed' THEN 2
                ELSE 3
            END,
            e.date ASC,
            o.created_at DESC"
    );
    $sth->execute();
    return $sth->fetchall_arrayref({});
}

sub handle_login {
    my $login = $cgi->param('login');
    my $password = $cgi->param('password');
    
    # Отладочная информация
    warn "Trying to login with: login=$login, password=$password";
    
    if (my $user = authenticate_user($login, $password)) {
        warn "Login successful for user: " . $user->{login};
        
        # Устанавливаем cookie
        my $cookie = $cgi->cookie(
            -name => 'user_id',
            -value => $user->{id},
            -expires => '+1h'
        );
        
        # Делаем редирект с установкой cookie
        print $cgi->header(
            -type => 'text/html',
            -charset => 'utf-8',
            -cookie => $cookie,
            -status => '302 Found',
            -location => 'http://localhost:8090/cgi-bin/index.cgi?action=home'
        );
        
        # Добавляем тело ответа для случаев, когда редирект не сработает
        print "Выполняется вход...\n";
        print '<script>window.location.href="http://localhost:8090/cgi-bin/index.cgi?action=home";</script>';
        
    } else {
        warn "Login failed for user: $login";
        print $cgi->header(
            -type => 'text/html',
            -charset => 'utf-8',
            -status => '302 Found',
            -location => 'http://localhost:8090/cgi-bin/index.cgi?action=login&error=1'
        );
        print "Перенаправление на страницу входа...\n";
        print '<script>window.location.href="http://localhost:8090/cgi-bin/index.cgi?action=login&error=1";</script>';
    }
}

sub handle_register {
    my $login = $cgi->param('login');
    my $password = $cgi->param('password');
    my $password_confirm = $cgi->param('password_confirm');
    
    unless ($password eq $password_confirm) {
        print $cgi->redirect('/cgi-bin/index.cgi?action=login&error=passwords_mismatch');
        return;
    }
    
    eval {
        my $sth = $dbh->prepare(
            "INSERT INTO users (login, password, role) VALUES (?, ?, 'user')"
        );
        $sth->execute($login, $password);
    };
    
    if ($@) {
        # Если ошибка при регистрации (например, логин уже занят)
        print $cgi->redirect('/cgi-bin/index.cgi?action=login&error=registration_failed');
    } else {
        # После успешной регистрации сразу авторизуем пользователя
        if (my $user = authenticate_user($login, $password)) {
            my $cookie = $cgi->cookie(
                -name => 'user_id',
                -value => $user->{id},
                -expires => '+1h'
            );
            print $cgi->header(
                -type => 'text/html',
                -charset => 'utf-8',
                -cookie => $cookie,
                -location => 'http://localhost:8090/cgi-bin/index.cgi?action=events'
            );
        } else {
            print $cgi->redirect('/cgi-bin/index.cgi?action=login');
        }
    }
}

sub handle_logout {
    # Удаляем cookie и делаем редирект на главную
    my $cookie = $cgi->cookie(
        -name => 'user_id',
        -value => '',
        -expires => '-1h'
    );

    # Отправляем все необходимые заголовки
    print $cgi->header(
        -type => 'text/html',
        -charset => 'utf-8',
        -cookie => $cookie,
        -status => '302 Found',
        -location => 'http://localhost:8090/cgi-bin/index.cgi?action=home'
    );
    
    # Добавляем тело ответа для случаев, когда редирект не сработает
    print "Выполняется выход...\n";
    print '<script>window.location.href="http://localhost:8090/cgi-bin/index.cgi?action=home";</script>';
}

sub handle_add_to_cart {
    unless ($current_user) {
        print $cgi->header(-type => 'application/json', -charset => 'utf-8');
        my $response = $json->encode({
            success => 0,
            error => 'Необходима авторизация'
        });
        print $response;
        return;
    }
    
    my $event_id = $cgi->param('event_id');
    my $quantity = $cgi->param('quantity');
    my $zone_id = $cgi->param('zone_id');
    my $seat_numbers = $cgi->param('seat_numbers'); # Comma-separated list of seat numbers
    
    # Validate required parameters
    unless ($event_id && $quantity) {
        print $cgi->header(-type => 'application/json', -charset => 'utf-8');
        my $response = $json->encode({
            success => 0,
            error => 'Отсутствуют обязательные параметры',
            debug => {
                event_id => $event_id,
                quantity => $quantity
            }
        });
        print $response;
        return;
    }
    
    # If zone_id and seat_numbers are not provided, redirect to zone selection page
    unless ($zone_id && $seat_numbers) {
        print $cgi->redirect("?action=select_zone&event_id=$event_id&quantity=$quantity");
        return;
    }
    
    # Parse seat numbers
    my @seat_array = split(',', $seat_numbers);
    
    # Validate that we have the correct number of seats
    unless (@seat_array == $quantity) {
        print $cgi->header(-type => 'application/json', -charset => 'utf-8');
        my $response = $json->encode({
            success => 0,
            error => 'Количество выбранных мест не соответствует указанному количеству билетов',
            debug => {
                requested_quantity => $quantity,
                selected_seats => scalar(@seat_array)
            }
        });
        print $response;
        return;
    }
    
    # Get zone details
    my $zone = $dbh->selectrow_hashref(
        "SELECT z.*, ez.available_seats 
         FROM zones z 
         JOIN event_zones ez ON z.id = ez.zone_id 
         WHERE ez.event_id = ? AND z.id = ?",
        undef,
        $event_id,
        $zone_id
    );
    
    unless ($zone) {
        print $cgi->header(-type => 'application/json', -charset => 'utf-8');
        my $response = $json->encode({
            success => 0,
            error => 'Зона не найдена',
            debug => {
                event_id => $event_id,
                zone_id => $zone_id
            }
        });
        return;
    }
    
    if ($zone->{available_seats} < $quantity) {
        print $cgi->header(-type => 'application/json', -charset => 'utf-8');
        print $json->encode({ 
            success => 0, 
            error => 'Недостаточно свободных мест',
            debug => {
                available => $zone->{available_seats},
                requested => $quantity
            }
        });
        return;
    }
    
    # Check if any of the requested seats are already reserved
    my $reserved_seats_query = $dbh->prepare(
        "SELECT seat_number FROM reserved_seats 
         WHERE event_id = ? AND zone_id = ? AND seat_number IN (" . join(',', ('?') x @seat_array) . ")"
    );
    
    $reserved_seats_query->execute($event_id, $zone_id, @seat_array);
    my $reserved_seats = $reserved_seats_query->fetchall_arrayref();
    
    if (@$reserved_seats) {
        my @already_reserved = map { $_->[0] } @$reserved_seats;
        print $cgi->header(-type => 'application/json', -charset => 'utf-8');
        print $json->encode({ 
            success => 0, 
            error => 'Некоторые выбранные места уже заняты',
            debug => {
                reserved_seats => \@already_reserved
            }
        });
        return;
    }
    
    # Add to cart and temporarily reserve seats
    my $total_price = $zone->{price} * $quantity;
    
    # Begin transaction
    $dbh->begin_work;
    
    eval {
        # Insert cart item
        my $cart_sth = $dbh->prepare(
            "INSERT INTO cart (user_id, event_id, zone_id, quantity, total_price, created_at, seat_numbers) 
             VALUES (?, ?, ?, ?, ?, datetime('now'), ?)"
        );
        
        $cart_sth->execute(
            $current_user->{id}, 
            $event_id, 
            $zone_id, 
            $quantity, 
            $total_price, 
            $seat_numbers
        );
        
        # Reserve each seat
        my $reserve_sth = $dbh->prepare(
            "INSERT INTO reserved_seats (event_id, zone_id, seat_number, user_id, reservation_type, reservation_time) 
             VALUES (?, ?, ?, ?, 'cart', datetime('now'))"
        );
        
        foreach my $seat_num (@seat_array) {
            $reserve_sth->execute($event_id, $zone_id, $seat_num, $current_user->{id});
        }
        
        # Update available seats in the zone
        my $update_zone_sth = $dbh->prepare(
            "UPDATE event_zones 
             SET available_seats = available_seats - ? 
             WHERE event_id = ? AND zone_id = ?"
        );
        
        $update_zone_sth->execute($quantity, $event_id, $zone_id);
        
        $dbh->commit;
    };
    
    if ($@) {
        $dbh->rollback;
        print $cgi->header(-type => 'application/json', -charset => 'utf-8');
        print $json->encode({ 
            success => 0, 
            error => 'Ошибка при добавлении в корзину',
            debug => {
                error => $@
            }
        });
        return;
    }
    
    print $cgi->header(-type => 'application/json', -charset => 'utf-8');
    print $json->encode({ 
        success => 1, 
        message => 'Билеты добавлены в корзину',
        debug => {
            event_id => $event_id,
            zone_id => $zone_id,
            quantity => $quantity,
            total_price => $total_price,
            seat_numbers => \@seat_array
        }
    });
}

# Modify handle_select_zone to include reserved seats information
sub handle_select_zone {
    my $event_id = $cgi->param('event_id');
    unless ($event_id) {
        print $cgi->redirect('?action=events');
        return;
    }
    
    # Get event details
    my $event = $dbh->selectrow_hashref(
        "SELECT * FROM events WHERE id = ?", 
        undef, 
        $event_id
    );
    
    unless ($event) {
        print $cgi->header(-type => 'text/html', -charset => 'utf-8');
        print "Мероприятие не найдено";
        return;
    }
    
    # Get the single hall zone
    my $zone = $dbh->selectrow_hashref(
        "SELECT z.*, ez.available_seats 
         FROM zones z
         JOIN event_zones ez ON z.id = ez.zone_id
         WHERE ez.event_id = ?
         LIMIT 1", 
        undef, 
        $event_id
    );
    
    unless ($zone) {
        print $cgi->header(-type => 'text/html', -charset => 'utf-8');
        print "Для данного мероприятия не найдены зоны";
        return;
    }
    
    # Get reserved seats count
    my $reserved_seats_count = $dbh->selectrow_array(
        "SELECT COUNT(*) 
         FROM orders 
         WHERE event_id = ? AND status = 'confirmed'", 
        undef, 
        $event_id
    ) || 0;
    
    # Calculate available seats
    my $available_seats = $zone->{available_seats} - $reserved_seats_count;
    
    # Render template with event and zone info
    print $cgi->header(-type => 'text/html', -charset => 'utf-8');
    print template('select_zone.html', {
        event => $event,
        zone => $zone,
        available_seats => $available_seats,
        max_quantity => 10,  # Set reasonable max quantity
        user => $current_user
    });
}

sub handle_remove_from_cart {
    unless ($current_user) {
        print $cgi->header(-type => 'application/json');
        print $json->encode({ success => 0, message => 'Необходимо войти в систему' });
        return;
    }
    
    my $event_id = $cgi->param('event_id');
    my $zone_id = $cgi->param('zone_id');
    
    # Begin transaction
    $dbh->begin_work;
    
    eval {
        # Get the cart item to get seat numbers before deleting
        my $cart_item = $dbh->selectrow_hashref(
            "SELECT * FROM cart 
             WHERE user_id = ? AND event_id = ? AND zone_id = ?",
            undef,
            $current_user->{id}, $event_id, $zone_id
        );
        
        if ($cart_item) {
            # Delete seat reservations
            if ($cart_item->{seat_numbers}) {
                my @seat_numbers = split(',', $cart_item->{seat_numbers});
                
                my $delete_reservations = $dbh->prepare(
                    "DELETE FROM reserved_seats 
                     WHERE event_id = ? AND zone_id = ? AND user_id = ? AND seat_number = ? AND reservation_type = 'cart'"
                );
                
                foreach my $seat_num (@seat_numbers) {
                    $delete_reservations->execute($event_id, $zone_id, $current_user->{id}, $seat_num);
                }
                
                # Update available seats count
                my $update_seats = $dbh->prepare(
                    "UPDATE event_zones 
                     SET available_seats = available_seats + ? 
                     WHERE event_id = ? AND zone_id = ?"
                );
                
                $update_seats->execute($cart_item->{quantity}, $event_id, $zone_id);
            }
        }
        
        # Delete the cart item
        my $delete_cart = $dbh->prepare(
            "DELETE FROM cart 
             WHERE user_id = ? AND event_id = ? AND zone_id = ?"
        );
        
        $delete_cart->execute($current_user->{id}, $event_id, $zone_id);
        
        $dbh->commit;
    };
    
    if ($@) {
        $dbh->rollback;
        print $cgi->header(-type => 'application/json');
        print $json->encode({ success => 0, message => 'Ошибка при удалении из корзины', error => $@ });
        return;
    }
    
    print $cgi->header(-type => 'application/json');
    print $json->encode({ success => 1, message => 'Билет удален из корзины' });
}

sub handle_checkout {
    unless ($current_user) {
        print $cgi->redirect('?action=login');
        return;
    }
    
    # Get cart items
    my $cart_items = get_cart_items($current_user->{id});
    
    unless (@$cart_items) {
        print $cgi->redirect('?action=cart');
        return;
    }
    
    # Start transaction
    $dbh->begin_work;
    
    eval {
        foreach my $item (@$cart_items) {
            # Check if seats are still available (should be, as they're reserved in the cart)
            my $zone = $dbh->selectrow_hashref(
                "SELECT available_seats FROM event_zones 
                 WHERE event_id = ? AND zone_id = ?",
                undef,
                $item->{event_id},
                $item->{zone_id}
            );
            
            unless ($zone && $zone->{available_seats} >= 0) {
                die "Недостаточно свободных мест в зоне " . $item->{zone_name};
            }
            
            # Create order
            my $order_sth = $dbh->prepare(
                "INSERT INTO orders (user_id, event_id, zone_id, quantity, total_price, status, created_at, seat_numbers) 
                 VALUES (?, ?, ?, ?, ?, 'pending', datetime('now'), ?)"
            );
            
            $order_sth->execute(
                $current_user->{id},
                $item->{event_id},
                $item->{zone_id},
                $item->{quantity},
                $item->{total_price},
                $item->{seat_numbers}
            );
            
            my $order_id = $dbh->last_insert_id("", "", "orders", "");
            
            # Update seat reservations from 'cart' to 'order'
            if ($item->{seat_numbers}) {
                my @seat_numbers = split(',', $item->{seat_numbers});
                
                my $update_reservations = $dbh->prepare(
                    "UPDATE reserved_seats 
                     SET reservation_type = 'order', reservation_time = datetime('now')
                     WHERE event_id = ? AND zone_id = ? AND user_id = ? AND seat_number = ? AND reservation_type = 'cart'"
                );
                
                foreach my $seat_num (@seat_numbers) {
                    $update_reservations->execute($item->{event_id}, $item->{zone_id}, $current_user->{id}, $seat_num);
                }
            }
            
            # Note: We don't need to update available_seats here as they were already 
            # decremented when adding to cart
        }
        
        # Clear cart
        my $clear_cart = $dbh->prepare("DELETE FROM cart WHERE user_id = ?");
        $clear_cart->execute($current_user->{id});
        
        $dbh->commit;
    };
    
    if ($@) {
        $dbh->rollback;
        print $cgi->redirect('?action=cart&error=' . uri_escape($@));
        return;
    }
    
    print $cgi->redirect('?action=cart&success=1');
}

sub handle_create_event {
    unless ($current_user && $current_user->{role} eq 'manager') {
        print $cgi->redirect('?action=home');
        return;
    }
    
    my $title = Encode::decode_utf8($cgi->param('title'));
    my $performers = Encode::decode_utf8($cgi->param('performers'));
    my $venue = Encode::decode_utf8($cgi->param('venue'));
    my $description = Encode::decode_utf8($cgi->param('description'));
    my $date = $cgi->param('date');
    my $time = $cgi->param('time');
    
    # Start transaction
    $dbh->begin_work;
    
    eval {
        # Insert event
        my $sth = $dbh->prepare(
            "INSERT INTO events (title, performers, venue, description, date, time) 
             VALUES (?, ?, ?, ?, ?, ?)"
        );
        $sth->execute($title, $performers, $venue, $description, $date, $time);
        my $event_id = $dbh->last_insert_id("", "", "events", "");
        
        # Insert zones for the event
        my $zone_sth = $dbh->prepare(
            "INSERT INTO event_zones (event_id, zone_id, available_seats) VALUES (?, ?, ?)"
        );
        
        # Get all zones
        my $zones = get_all_zones();
        
        foreach my $zone (@$zones) {
            my $zone_price = $cgi->param("zone_price_" . $zone->{id});
            my $zone_seats = $cgi->param("zone_seats_" . $zone->{id});
            
            if ($zone_seats > 0) {
                $zone_sth->execute($event_id, $zone->{id}, $zone_seats);
            }
        }
        
        $dbh->commit;
    };
    
    if ($@) {
        $dbh->rollback;
        die "Error creating event: $@";
    }
    
    print $cgi->redirect('?action=manager');
}

sub handle_update_order_status {
    unless ($current_user && ($current_user->{role} eq 'manager' || $current_user->{role} eq 'admin')) {
        print $cgi->header(
            -type => 'text/html',
            -charset => 'utf-8',
            -status => '302 Found',
            -location => 'http://localhost:8090/cgi-bin/index.cgi?action=login'
        );
        print "Перенаправление на страницу входа...\n";
        print '<script>window.location.href="http://localhost:8090/cgi-bin/index.cgi?action=login";</script>';
        return;
    }
    
    my $order_id = $cgi->param('order_id');
    my $status = $cgi->param('status');
    
    eval {
        my $sth = $dbh->prepare(
            "UPDATE orders SET status = ? WHERE id = ?"
        );
        $sth->execute($status, $order_id);
    };
    
    print $cgi->header(
        -type => 'text/html',
        -charset => 'utf-8',
        -status => '302 Found',
        -location => 'http://localhost:8090/cgi-bin/index.cgi?action=manager'
    );
    print "Перенаправление в панель менеджера...\n";
    print '<script>window.location.href="http://localhost:8090/cgi-bin/index.cgi?action=manager";</script>';
}

sub handle_update_user_role {
    unless ($current_user && $current_user->{role} eq 'admin') {
        print $cgi->header(
            -type => 'text/html',
            -charset => 'utf-8',
            -status => '302 Found',
            -location => 'http://localhost:8090/cgi-bin/index.cgi?action=login'
        );
        print "Перенаправление на страницу входа...\n";
        print '<script>window.location.href="http://localhost:8090/cgi-bin/index.cgi?action=login";</script>';
        return;
    }
    
    my $user_id = $cgi->param('user_id');
    my $role = $cgi->param('role');
    
    eval {
        my $sth = $dbh->prepare(
            "UPDATE users SET role = ? WHERE id = ?"
        );
        $sth->execute($role, $user_id);
    };
    
    print $cgi->header(
        -type => 'text/html',
        -charset => 'utf-8',
        -status => '302 Found',
        -location => 'http://localhost:8090/cgi-bin/index.cgi?action=admin'
    );
    print "Перенаправление в админ-панель...\n";
    print '<script>window.location.href="http://localhost:8090/cgi-bin/index.cgi?action=admin";</script>';
}

sub handle_delete_user {
    unless ($current_user && $current_user->{role} eq 'admin') {
        print $cgi->redirect('?action=login');
        return;
    }
    
    my $user_id = $cgi->param('user_id');
    
    eval {
        my $sth = $dbh->prepare("DELETE FROM users WHERE id = ?");
        $sth->execute($user_id);
    };
    
    print $cgi->redirect('?action=admin');
}

sub get_all_zones {
    my $sth = $dbh->prepare("SELECT * FROM zones ORDER BY name");
    $sth->execute();
    my $zones = $sth->fetchall_arrayref({});
    
    # Ensure UTF-8 encoding for text fields
    foreach my $zone (@$zones) {
        $zone->{name} = Encode::decode_utf8($zone->{name});
        $zone->{description} = Encode::decode_utf8($zone->{description});
    }
    
    return $zones;
}

sub get_event_zones {
    my ($event_id) = @_;
    
    my $sth = $dbh->prepare(
        "SELECT z.*, ez.available_seats 
         FROM zones z 
         JOIN event_zones ez ON z.id = ez.zone_id 
         WHERE ez.event_id = ?"
    );
    $sth->execute($event_id);
    my $zones = $sth->fetchall_arrayref({});
    
    # Ensure UTF-8 encoding for text fields
    foreach my $zone (@$zones) {
        $zone->{name} = Encode::decode_utf8($zone->{name});
        $zone->{description} = Encode::decode_utf8($zone->{description});
    }
    
    return $zones;
}

sub handle_add_event {
    unless ($current_user && ($current_user->{role} eq 'admin' || $current_user->{role} eq 'manager')) {
        print $cgi->redirect('?action=login');
        return;
    }
    
    my $title = $cgi->param('title');
    my $performers = $cgi->param('performers');
    my $venue = $cgi->param('venue');
    my $description = $cgi->param('description');
    my $date = $cgi->param('date');
    my $time = $cgi->param('time');
    my $price = $cgi->param('price');
    
    # Fixed seat number for the entire hall
    my $available_seats = 170; # Fixed total seats in our theater hall
    
    # Validate inputs
    unless ($title && $date && $time && $price) {
        print $cgi->header(-type => 'text/html', -charset => 'utf-8');
        print "Отсутствуют обязательные поля";
        return;
    }
    
    # Start transaction
    $dbh->begin_work;
    
    eval {
        # Insert new event
        my $event_sth = $dbh->prepare(
            "INSERT INTO events (title, performers, venue, description, date, time, price, available_seats) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        );
        
        $event_sth->execute($title, $performers, $venue, $description, $date, $time, $price, $available_seats);
        my $event_id = $dbh->last_insert_id("", "", "events", "");
        
        # Create a single zone for the entire hall
        my $zone_name = "Зал";
        my $zone_price = $price;
        
        # Check if this zone already exists
        my $zone_id;
        my $existing_zone = $dbh->selectrow_hashref(
            "SELECT id FROM zones WHERE name = ?", 
            undef, 
            $zone_name
        );
        
        if ($existing_zone) {
            $zone_id = $existing_zone->{id};
        } else {
            # Create new zone
            my $zone_sth = $dbh->prepare(
                "INSERT INTO zones (name, price, total_seats, description) 
                 VALUES (?, ?, ?, ?)"
            );
            
            $zone_sth->execute(
                $zone_name, 
                $zone_price, 
                $available_seats, 
                "Единый зал театра"
            );
            
            $zone_id = $dbh->last_insert_id("", "", "zones", "");
        }
        
        # Connect zone to event
        my $event_zone_sth = $dbh->prepare(
            "INSERT INTO event_zones (event_id, zone_id, available_seats) 
             VALUES (?, ?, ?)"
        );
        
        $event_zone_sth->execute($event_id, $zone_id, $available_seats);
        
        $dbh->commit;
    };
    
    if ($@) {
        $dbh->rollback;
        print $cgi->header(-type => 'text/html', -charset => 'utf-8');
        print "Error creating event: $@";
        return;
    }
    
    # Redirect back to admin page with tab parameter
    print $cgi->redirect('?action=admin&tab=add-event&success=1');
} 