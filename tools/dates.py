"""The date a piece was written.

NOT the file mtime: adding a missing H1 to two old essays moved them to the top
of the index, dated today. mtime answers "when was this file last touched",
which is a different question. git's add-date answers the one I want and no
later edit moves it.
"""
import subprocess, datetime, pathlib


def add_dates(repo, rel_dir):
    """-> {filename: datetime(utc)} for every file ever ADDED under rel_dir."""
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "--diff-filter=A", "--reverse",
         "--date=iso-strict", "--format=@%aI", "--name-only", "--", rel_dir],
        capture_output=True, text=True, check=True).stdout
    dates, cur = {}, None
    for line in out.split("\n"):
        if line.startswith("@"):
            cur = datetime.datetime.fromisoformat(line[1:]).astimezone(datetime.timezone.utc)
        elif line.strip() and cur:
            name = pathlib.PurePosixPath(line.strip()).name
            dates.setdefault(name, cur)          # first add wins
    return dates


def date_for(path, table):
    d = table.get(path.name)
    if d:
        return d
    return datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc)
