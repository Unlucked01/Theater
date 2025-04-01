FROM httpd:2.4

# Install Perl and required modules
RUN apt-get update && apt-get install -y \
    perl \
    libcgi-pm-perl \
    libdbd-sqlite3-perl \
    libtemplate-perl \
    libcrypt-pbkdf2-perl \
    libjson-perl \
    libdatetime-perl \
    libmime-base64-perl \
    libdb-file-lock-perl \
    libdigest-sha-perl \
    wget \
    sudo \
    make \
    gcc \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Perl modules via CPAN
RUN cpan -T CGI::Simple \
    && cpan -T DBI \
    && cpan -T Template \
    && cpan -T DateTime \
    && cpan -T File::Spec \
    && cpan -T MIME::Base64 \
    && cpan -T Encode \
    && cpan -T JSON::PP \
    && cpan -T HTML::Template

# Create necessary directories
RUN mkdir -p /usr/local/apache2/htdocs/{templates,static/{css,js,images}} \
    && mkdir -p /usr/local/apache2/data \
    && mkdir -p /usr/local/apache2/database

# Copy configuration
COPY conf/httpd.conf /usr/local/apache2/conf/httpd.conf

# Copy web content
COPY index.html /usr/local/apache2/htdocs/
COPY templates/ /usr/local/apache2/htdocs/templates/
COPY static/ /usr/local/apache2/htdocs/static/
COPY cgi-bin/ /usr/local/apache2/cgi-bin/
COPY database/init.sql /usr/local/apache2/database/

# Set up entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set proper permissions
RUN chmod +x /usr/local/apache2/cgi-bin/*.cgi \
    && chown -R www-data:www-data /usr/local/apache2/htdocs \
    && chown -R www-data:www-data /usr/local/apache2/cgi-bin \
    && chown -R www-data:www-data /usr/local/apache2/data \
    && chown -R www-data:www-data /usr/local/apache2/database \
    && chown -R www-data:www-data /usr/local/apache2/conf \
    && chmod -R 755 /usr/local/apache2/htdocs/templates

# Verify template files
RUN ls -la /usr/local/apache2/htdocs/templates/

EXPOSE 80

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["httpd-foreground"]