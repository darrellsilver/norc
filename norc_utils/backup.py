
import os

from norc.settings import (NORC_LOG_DIR, BACKUP_SYSTEM,
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME)
from norc.norc_utils.log import make_log

if BACKUP_SYSTEM == 'AmazonS3':
    from norc.norc_utils.aws import set_s3_key


def s3_backup(fp, target):
    for i in range(0, 3):
        try:
            set_s3_key(target, fp)
            return True
        except:
            pass
    return False

BACKUP_SYSTEMS = {
    'AmazonS3': s3_backup,
}

def backup_log(log_path):
    try:
        fp = open(os.path.join(NORC_LOG_DIR, log_path), 'r')
    except IOError:
        return False
    target = os.path.join('norc_logs/', log_path)
    try:
        return _backup_file(fp, target)
    except:
        log = make_log(log_path)
        log.error('Could not back up log file "%s"' % log_path, trace=True)
        return False

def _backup_file(fp, target):
    if BACKUP_SYSTEM:
        return BACKUP_SYSTEMS[BACKUP_SYSTEM](fp, target)
    else:
        return False
