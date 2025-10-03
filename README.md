# Mod Resources
A Github repository for hosting web content needed by **@heyitsfuzs** mods.

## `./gradle`
Contains Gradle build scripts applied to all mod projects that are using a multi-loader development setup.

## `./maven`
A Maven repository where some **@heyitsfuzs** mods with a public api are published. Resources found in this directory can be accessed from a Gradle buildscript as shown below.

```groovy
repositories {
    maven {
        name = "Fuzs Mod Resources"
        url = "https://raw.githubusercontent.com/Fuzss/modresources/main/maven/"
    }
}

dependencies {
    // Common
    api "fuzs.<modId>:<modId>-common:<modVersion>"
    // Fabric
    modApi "fuzs.<modId>:<modId>-fabric:<modVersion>"
    // NeoForge
    api "fuzs.<modId>:<modId>-neoforge:<modVersion>"
    // Forge
    api fg.deobf("fuzs.<modId>:<modId>-forge:<modVersion>")
}
```

## `./mods`
Data for individual mods regarding distributions and installation information.

## `./pages`
Content for **@heyitsfuzs** mod pages found on [CurseForge](https://www.curseforge.com/members/fuzs/projects) and [Modrinth](https://modrinth.com/user/Fuzs). The full pages are generated from individual files using a private tool.

## `./scripts`
Collection of Python scripts for maintaining **@heyitsfuzs** mods.

## `./update`
Mod files for NeoForge's / Forge's update checker system. The files are automatically refreshed locally from Gradle buildscripts whenever a new NeoForge / Forge release is published.
