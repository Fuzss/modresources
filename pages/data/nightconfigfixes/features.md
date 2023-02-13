+ The issue occurs randomly where a config file will just go blank and Night Config will throw the exception when trying to read that file next time.
+ Night Config Fixes makes sure this no longer crashes the game, but instead catches the exception and simply recreate the config from its default values.
+ Modpacks must put their configured config files in the `defaultconfigs` directory instead of `config` so the correct values can be restored!
+ Find out more details on the [GitHub repository](https://github.com/Fuzss/nightconfigfixes)!
+ Also includes an additional option to generate server configs on Forge in the global `config` directory instead of locally per world in `serverconfig`!