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

# Включаем UTF-8 для всех операций ввода/вывода
binmode(STDIN, ':utf8');
binmode(STDOUT, ':utf8');
binmode(STDERR, ':utf8');

# Создаем JSON кодировщик с поддержкой UTF-8
my $json = JSON::PP->new->utf8(1);

# Инициализация CGI
my $cgi = CGI::Simple->new;
$CGI::Simple::DISABLE_UPLOADS = 0;
$CGI::Simple::POST_MAX = 1024 * 1024;

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

# Подключение к базе данных
my $db_file = File::Spec->catfile($project_root, 'database', 'theater.db');
my $dbh = DBI->connect("dbi:SQLite:dbname=$db_file", "", "", {
    RaiseError => 1,
    AutoCommit => 1,
    sqlite_unicode => 1,
    sqlite_utf8 => 1
}) or die $DBI::errstr;
$dbh->do("PRAGMA encoding = 'UTF-8'");

# Инициализация шаблонизатора
my $template = Template->new({
    INCLUDE_PATH => File::Spec->catdir($project_root, 'templates'),
    ENCODING => 'utf8',
    UNICODE => 1
});

# Получение текущего пользователя из сессии
my $current_user = get_current_user();

# Не выводим заголовок для действий, которые сами управляют заголовками
unless ($action eq 'logout' || $action eq 'add_to_cart' || $action eq 'register' || $action eq 'do_login') {
    print $cgi->header(-type => 'text/html', -charset => 'utf-8');
}

my %routes = (
    'home' => \&show_home,
    'events' => \&show_events,
    'event' => \&show_event,
    'cart' => \&show_cart,
    'login' => \&show_login,
    'do_login' => \&handle_login,
    'register' => \&handle_register,
    'logout' => \&handle_logout,
    'add_to_cart' => \&handle_add_to_cart,
    'remove_from_cart' => \&handle_remove_from_cart,
    'checkout' => \&handle_checkout,
    'admin' => \&show_admin,
    'manager' => \&show_manager,
    'create_event' => \&handle_create_event,
    'update_order_status' => \&handle_update_order_status,
    'update_user_role' => \&handle_update_user_role,
    'delete_user' => \&handle_delete_user
);

if (exists $routes{$action}) {
    $routes{$action}->();
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
            $error_message = Encode::decode_utf8('Пароли не совпадают');
        } elsif ($error eq 'registration_failed') {
            $error_message = Encode::decode_utf8('Ошибка при регистрации. Возможно, такой логин уже занят');
        } elsif ($error eq '1') {
            $error_message = Encode::decode_utf8('Неправильный логин или пароль');
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
    
    my $vars = {
        title => 'Админ-панель',
        user => $current_user,
        users => get_all_users(),
        events => get_all_events(),
        orders => get_all_orders(),
        total_orders => $stats->{total_orders},
        active_orders => $stats->{active_orders},
        total_events => $stats->{total_events},
        event_stats => $stats->{event_stats}
    };
    
    $template->process('admin.html', $vars)
        or die $template->error();
}

sub show_manager {
    unless ($current_user && ($current_user->{role} eq 'manager' || $current_user->{role} eq 'admin')) {
        print $cgi->redirect('?action=login');
        return;
    }
    
    my $vars = {
        title => 'Панель менеджера',
        user => $current_user,
        events => get_manager_events($current_user->{id}),
        orders => get_manager_orders($current_user->{id})
    };
    
    $template->process('manager.html', $vars)
        or die $template->error();
}

sub show_404 {
    my $vars = {
        title => 'Страница не найдена',
        user => $current_user
    };
    
    print $cgi->header(-status => '404 Not Found');
    $template->process('404.html', $vars)
        or die $template->error();
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
            -location => 'http://localhost:8080/cgi-bin/index.cgi?action=events'
        );
        
    } else {
        warn "Login failed for user: $login";
        print $cgi->redirect('/cgi-bin/index.cgi?action=login&error=1');
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
                -location => '/cgi-bin/index.cgi?action=events'
            );
        } else {
            print $cgi->redirect('/cgi-bin/index.cgi?action=login');
        }
    }
}

sub handle_logout {
    # Удаляем cookie и делаем редирект на главную
    print $cgi->header(
        -type => 'text/html',
        -charset => 'utf-8',
        -cookie => $cgi->cookie(
            -name => 'user_id',
            -value => '',
            -expires => '-1h'
        ),
        -location => '/cgi-bin/index.cgi?action=home'
    );
}

sub handle_add_to_cart {
    unless ($current_user) {
        print $cgi->header(-type => 'application/json', -charset => 'utf-8');
        print $json->encode({ success => 0, error => 'Необходима авторизация' });
        return;
    }
    
    my $event_id = $cgi->param('event_id');
    my $quantity = $cgi->param('quantity') || 1;
    
    eval {
        my $sth = $dbh->prepare(
            "INSERT INTO orders (user_id, event_id, quantity, total_price, status, created_at) 
             SELECT ?, ?, ?, price * ?, 'pending', datetime('now')
             FROM events WHERE id = ?"
        );
        $sth->execute($current_user->{id}, $event_id, $quantity, $quantity, $event_id);
        
        # Обновляем количество доступных мест
        $sth = $dbh->prepare(
            "UPDATE events SET available_seats = available_seats - ?
             WHERE id = ? AND available_seats >= ?"
        );
        $sth->execute($quantity, $event_id, $quantity);
    };
    
    print $cgi->header(-type => 'application/json', -charset => 'utf-8');
    if ($@) {
        print $json->encode({ success => 0, error => 'Ошибка при добавлении в корзину' });
    } else {
        print $json->encode({ success => 1, message => 'Билет добавлен в корзину' });
    }
}

sub handle_remove_from_cart {
    unless ($current_user) {
        print $cgi->redirect('?action=login');
        return;
    }
    
    my $event_id = $cgi->param('event_id');
    
    eval {
        # Получаем информацию о заказе
        my $sth = $dbh->prepare(
            "SELECT id, quantity FROM orders 
             WHERE user_id = ? AND event_id = ? AND status = 'pending'
             LIMIT 1"
        );
        $sth->execute($current_user->{id}, $event_id);
        my $order = $sth->fetchrow_hashref;
        
        if ($order) {
            # Возвращаем билеты в доступные места
            $sth = $dbh->prepare(
                "UPDATE events 
                 SET available_seats = available_seats + ?
                 WHERE id = ?"
            );
            $sth->execute($order->{quantity}, $event_id);
            
            # Удаляем заказ
            $sth = $dbh->prepare("DELETE FROM orders WHERE id = ? AND user_id = ?");
            $sth->execute($order->{id}, $current_user->{id});
        }
    };
    
    if ($@) {
        warn "Error removing from cart: $@";
    }
    
    print $cgi->redirect('?action=cart');
}

sub handle_checkout {
    unless ($current_user) {
        print $cgi->redirect('?action=login');
        return;
    }
    
    eval {
        my $sth = $dbh->prepare(
            "UPDATE orders 
             SET status = 'confirmed' 
             WHERE user_id = ? AND status = 'pending'"
        );
        $sth->execute($current_user->{id});
    };
    
    print $cgi->redirect('?action=cart');
}

sub handle_create_event {
    unless ($current_user && ($current_user->{role} eq 'manager' || $current_user->{role} eq 'admin')) {
        print $cgi->redirect('?action=login');
        return;
    }
    
    # Получаем параметры с явным указанием кодировки
    my $title = Encode::decode_utf8($cgi->param('title'));
    my $performers = Encode::decode_utf8($cgi->param('performers'));
    my $venue = Encode::decode_utf8($cgi->param('venue'));
    my $description = Encode::decode_utf8($cgi->param('description'));
    my $date = $cgi->param('date');
    my $time = $cgi->param('time');
    my $price = $cgi->param('price');
    my $available_seats = $cgi->param('available_seats');
    
    # Отладочная информация
    warn "Creating event: title=$title, performers=$performers, venue=$venue, date=$date, time=$time, price=$price, seats=$available_seats";
    
    eval {
        my $sth = $dbh->prepare(
            "INSERT INTO events (title, performers, venue, description, date, time, price, available_seats)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        );
        $sth->execute($title, $performers, $venue, $description, $date, $time, $price, $available_seats);
    };
    
    if ($@) {
        warn "Error creating event: $@";
        print $cgi->redirect('?action=manager&error=create_failed');
    } else {
        print $cgi->redirect('?action=manager&success=created');
    }
}

sub handle_update_order_status {
    unless ($current_user && ($current_user->{role} eq 'manager' || $current_user->{role} eq 'admin')) {
        print $cgi->redirect('?action=login');
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
    
    print $cgi->redirect('?action=manager');
}

sub handle_update_user_role {
    unless ($current_user && $current_user->{role} eq 'admin') {
        print $cgi->redirect('?action=login');
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
    
    print $cgi->redirect('?action=admin');
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

# Вспомогательные функции
sub get_latest_events {
    my $sth = $dbh->prepare(
        "SELECT * FROM events 
         WHERE date >= date('now') 
         ORDER BY date, time 
         LIMIT 5"
    );
    $sth->execute();
    return $sth->fetchall_arrayref({});
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
            date >= date('now') DESC, -- Future events first
            date ASC,                 -- Then by date
            time ASC"                
    );
    $sth->execute();
    return $sth->fetchall_arrayref({});
}

sub get_cart_items {
    my ($user_id) = @_;
    
    my $sth = $dbh->prepare(
        "SELECT o.*, e.title, e.date, e.time, e.price 
         FROM orders o
         JOIN events e ON o.event_id = e.id
         WHERE o.user_id = ? AND o.status = 'pending'"
    );
    $sth->execute($user_id);
    return $sth->fetchall_arrayref({});
}

sub get_all_users {
    my $sth = $dbh->prepare("SELECT * FROM users ORDER BY id");
    $sth->execute();
    return $sth->fetchall_arrayref({});
}

sub get_all_orders {
    my $sth = $dbh->prepare(
        "SELECT o.*, u.login as user_login, e.title as event_title
         FROM orders o
         JOIN users u ON o.user_id = u.id
         JOIN events e ON o.event_id = e.id
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
                e.price as event_price
         FROM orders o
         JOIN users u ON o.user_id = u.id
         JOIN events e ON o.event_id = e.id
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

# Добавляем функцию для отображения отдельного мероприятия
sub show_event {
    my $event_id = $cgi->param('id');
    
    my $sth = $dbh->prepare(
        "SELECT * FROM events WHERE id = ?"
    );
    $sth->execute($event_id);
    my $event = $sth->fetchrow_hashref;
    
    unless ($event) {
        show_404();
        return;
    }
    
    my $vars = {
        title => $event->{title},
        user => $current_user,
        event => $event
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
        "SELECT e.title, COUNT(o.id) as sales 
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
    
    return {
        total_orders => $total_orders,
        active_orders => $active_orders,
        total_events => $total_events,
        event_stats => $event_stats
    };
} 