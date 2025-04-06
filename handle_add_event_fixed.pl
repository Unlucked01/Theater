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
    
    # Send proper redirect headers to ensure browser follows the redirect
    print $cgi->header(
        -status => '302 Found',
        -location => '?action=admin&tab=add-event&success=1',
        -type => 'text/html',
        -charset => 'utf-8'
    );
    
    # Add a message that would be displayed if the redirect fails
    print "Redirecting to admin page...";
    print '<script>window.location.href="?action=admin&tab=add-event&success=1";</script>';
} 