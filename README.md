# Flash Sync

Synchronize files to a flash drive intended for use in a simple MP3 player.
- Renames folders and MP3 files in source location to remove special characters.
- Uses rsync to synchronize files from a source folder to the chosen destination.
- Uses fatsort to ensure that the FAT orders the files in alphabetical order.
- Installs as a desktop and can be run directly from the terminal.

>Depends on fatsort, pkexec, rsync, and zenity packages.

## Help

```
Usage: flash-sync [options] [SOURCE] DEST

-c      clean (remove files from) DEST
-d      run in debug (set -x) mode
-h      show this help
-l      list files in DEST in disk order
-n      fix filenames in DEST to exclude special characters
-s      update FAT to sort files by name in DEST

If no options are given, update DEST with files from SOURCE.
If only DEST is given, list files at DEST (same as using -l option).
```
