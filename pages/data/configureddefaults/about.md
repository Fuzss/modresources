Configured Defaults serves a a utility for mod packs for copying absent files to the game or server directory from a default location provided by the `configureddefaults` folder.

Most importantly this helps mod pack makers with providing default mod config files, especially when those mods have been added to the pack via an update and would otherwise generate their missing configs themselves.
Any file and folder in the game directory is supported. 

Particularly `options.txt` enjoys special handling where missing entries in an existing file will be complemented from the file provided as a default.

Further instructions on how to use this mod are found in `configureddefaults/README.md` which generates after the game has run for the first time with the mod installed.
