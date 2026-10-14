#!/bin/bash
mkdir -p backups
filename="backups/backup_$(date +'%Y-%m-%d_%H%M%S').sql"

docker exec -t image_storage-postgres-1 pg_dump -U postgres --clean image_storage > "$filename"
echo "Бэкап сохранен в $filename"