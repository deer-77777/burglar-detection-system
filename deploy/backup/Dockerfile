FROM mysql:8.0

# mysql:8.0 already provides mysqldump and gzip; nothing else needed.
COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh

CMD ["/usr/local/bin/backup.sh"]
