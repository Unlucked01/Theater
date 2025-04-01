#!/usr/bin/perl
use strict;
use warnings;
use DBI;
use File::Spec;

# Определяем путь к файлам базы данных
my $db_dir = File::Spec->catdir('database');
my $db_file = File::Spec->catfile($db_dir, 'theater.db');
my $schema_file = File::Spec->catfile($db_dir, 'init.sql');

# Connect to database
my $dbh = DBI->connect("dbi:SQLite:dbname=$db_file", "", "", {
    RaiseError => 1,
    AutoCommit => 1
}) or die $DBI::errstr;

# Read and execute schema
open(my $fh, '<', $schema_file) or die "Cannot open $schema_file: $!";
my $schema = do { local $/; <$fh> };
close $fh;

# Split schema into individual statements and execute
my @statements = split /;/, $schema;
for my $statement (@statements) {
    next unless $statement =~ /\S/;  # Skip empty statements
    $dbh->do($statement) or die $dbh->errstr;
}

# Create admin user with plain password
my $admin_password = 'admin123';

$dbh->do("INSERT OR IGNORE INTO users (login, password, role) VALUES (?, ?, ?)",
    undef, 'admin', $admin_password, 'admin');

print "Database initialized successfully!\n";
$dbh->disconnect; 