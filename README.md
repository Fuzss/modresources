# Mod Resources

A GitHub repository for hosting web content used by **@heyitsfuzs** mods.

---

### `./gradle`

Contains legacy Gradle build scripts for multi-loader mod development setups.  
These scripts are no longer used on modern versions.

---

### `./maven`

A Maven repository for some **@heyitsfuzs** mods with a public API.  
Resources here can be accessed from a `build.gradle.kts` script:

```kotlin
repositories {
    maven {
        name = "Fuzs Mod Resources"
        url = uri("https://raw.githubusercontent.com/Fuzss/modresources/main/maven/")
    }
}

dependencies {
    // Common
    api("<modGroup>:<modId>-common:<modVersion>")
    // Fabric (Minecraft 26.1+)
    api("<modGroup>:<modId>-fabric:<modVersion>")
    // Fabric (Minecraft -26.1)
    modApi("<modGroup>:<modId>-fabric:<modVersion>")
    // NeoForge
    api("<modGroup>:<modId>-neoforge:<modVersion>")
    // Forge (Minecraft 1.21+)
    api("<modGroup>:<modId>-forge:<modVersion>")
    // Forge (Minecraft -1.21)
    api(fg.deobf("<modGroup>:<modId>-forge:<modVersion>"))
}
```

---

### `./mods`

Contains data for individual mods, including distributions and installation information.

---

### `./pages`

Content for **@heyitsfuzs** mod pages found on [CurseForge](https://www.curseforge.com/members/fuzs/projects) and [Modrinth](https://modrinth.com/user/Fuzs).  
Full pages are generated from individual files using a private tool.

---

### `./scripts`

Python scripts for various modding tasks, including porting and deployment of individual projects.

---

### `./update`

Mod files for NeoForge / Forge [update checker system](https://docs.neoforged.net/docs/misc/updatechecker).  
Files are automatically refreshed from Gradle buildscripts whenever a new NeoForge / Forge release is published.

This system has been replaced in modern versions by the built-in [Modrinth update checker implementation](https://docs.modrinth.com/api/operations/forgeupdates/).
