"""
Database backup manager for automated backups to local and cloud storage.
"""
import os
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, db_path="history.db", backup_dir="backups"):
        self.db_path = db_path
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self):
        """
        Create a timestamped backup of the database.
        Returns the backup file path.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"history_backup_{timestamp}.db"
        backup_path = self.backup_dir / backup_filename

        try:
            # Use SQLite backup API for safe backup
            source_conn = sqlite3.connect(self.db_path)
            backup_conn = sqlite3.connect(str(backup_path))

            with backup_conn:
                source_conn.backup(backup_conn)

            source_conn.close()
            backup_conn.close()

            # Get file size
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"Created backup: {backup_filename} ({size_mb:.2f} MB)")

            return str(backup_path)

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None

    def export_to_csv(self):
        """
        Export historical_flights table to CSV for redundancy.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"historical_flights_{timestamp}.csv"
        csv_path = self.backup_dir / csv_filename

        try:
            import csv
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("SELECT * FROM historical_flights")

            # Get column names
            columns = [description[0] for description in cursor.description]

            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(cursor.fetchall())

            conn.close()

            logger.info(f"Exported CSV: {csv_filename}")
            return str(csv_path)

        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return None

    def cleanup_old_backups(self, retention_days=30):
        """
        Remove backups older than retention_days.
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0

        for backup_file in self.backup_dir.glob("history_backup_*.db"):
            # Parse timestamp from filename
            try:
                timestamp_str = backup_file.stem.split('_', 2)[2]
                file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                if file_date < cutoff_date:
                    backup_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {backup_file.name}")

            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse backup filename: {backup_file.name}")

        logger.info(f"Cleanup complete. Deleted {deleted_count} old backups.")
        return deleted_count

    def upload_to_s3(self, backup_path, bucket_name=None):
        """
        Upload backup to AWS S3 (optional).
        Requires: pip install boto3
        """
        if not bucket_name:
            bucket_name = os.getenv("S3_BACKUP_BUCKET")

        if not bucket_name:
            logger.warning("S3 bucket not configured, skipping cloud backup")
            return False

        try:
            import boto3

            s3_client = boto3.client('s3')
            backup_filename = Path(backup_path).name

            s3_client.upload_file(
                backup_path,
                bucket_name,
                f"kpuw_backups/{backup_filename}"
            )

            logger.info(f"Uploaded to S3: {bucket_name}/kpuw_backups/{backup_filename}")
            return True

        except ImportError:
            logger.warning("boto3 not installed, skipping S3 upload")
            return False
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

    def get_backup_stats(self):
        """
        Get statistics about backups.
        """
        backups = list(self.backup_dir.glob("history_backup_*.db"))

        if not backups:
            return {
                "count": 0,
                "total_size_mb": 0,
                "oldest": None,
                "newest": None
            }

        total_size = sum(b.stat().st_size for b in backups)

        # Parse dates from filenames
        dates = []
        for backup in backups:
            try:
                timestamp_str = backup.stem.split('_', 2)[2]
                file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                dates.append(file_date)
            except (ValueError, IndexError):
                continue

        return {
            "count": len(backups),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest": min(dates).strftime("%Y-%m-%d %H:%M") if dates else None,
            "newest": max(dates).strftime("%Y-%m-%d %H:%M") if dates else None
        }

def scheduled_backup():
    """
    Function to be called by scheduler for automated backups.
    """
    backup_manager = BackupManager()

    # Create database backup
    backup_path = backup_manager.create_backup()

    if backup_path:
        # Upload to S3 if configured
        if os.getenv("BACKUP_ENABLED", "false").lower() == "true":
            backup_manager.upload_to_s3(backup_path)

        # Also export to CSV
        backup_manager.export_to_csv()

    # Cleanup old backups
    retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
    backup_manager.cleanup_old_backups(retention_days)

    # Log statistics
    stats = backup_manager.get_backup_stats()
    logger.info(f"Backup stats: {stats}")

if __name__ == "__main__":
    # Manual backup execution
    print("Starting database backup...")
    scheduled_backup()
    print("Backup complete!")
