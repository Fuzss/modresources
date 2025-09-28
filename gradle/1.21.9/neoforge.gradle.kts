plugins {
    alias(libs.plugins.shadow)
}

architectury {
    platformSetupLoomIde()
    neoForge()
}

loom {
    accessWidenerPath.set(project(":Common").loom.accessWidenerPath)

    runs.configureEach {
        ideConfigGenerated(true)
        runDir = project.file("../run").absolutePath
        vmArgs(
            "-Xms1G",
            "-Xmx4G",
            "-Dmixin.debug.export=true",
            "-Dlog4j2.configurationFile=https://raw.githubusercontent.com/Fuzss/modresources/main/gradle/${libs.versions.minecraft.get()}/log4j.xml",
            "-Dpuzzleslib.isDevelopmentEnvironment=true",
            "-D${project.property("modId")}.isDevelopmentEnvironment=true"
        )
    }

    runs {
        named("client") {
            client()
            configName = "NeoForge Client ${libs.versions.minecraft.get()}"
            programArgs("--username", "Player####")
        }
        named("server") {
            server()
            configName = "NeoForge Server ${libs.versions.minecraft.get()}"
        }
        register("data") {
            clientData()
            configName = "NeoForge Data ${libs.versions.minecraft.get()}"
            programArgs("--all", "--mod", project.property("modId") as String)
            programArgs(
                "--existing",
                project(":Common").file("src/main/resources").absolutePath
            )
            programArgs(
                "--output",
                project(":Common").file("src/generated/resources").absolutePath
            )
        }
    }
}

configurations {
    create("common")
    create("shadowCommon")

    compileClasspath.get().extendsFrom(getByName("common"))
    runtimeClasspath.get().extendsFrom(getByName("common"))
    getByName("developmentNeoForge").extendsFrom(getByName("common"))
}

repositories {
    maven {
        name = "NeoForged"
        url = uri("https://maven.neoforged.net/releases/")
    }
    maven {
        name = "NeoForged Alpha"
        url = uri("https://prmaven.neoforged.net/NeoForge/pr2639")
        content { includeModule("net.neoforged", "neoforge") }
    }
    maven {
        name = "TheIllusiveC4"
        url = uri("https://maven.theillusivec4.top/")
    }
    maven {
        name = "OctoStudios"
        url = uri("https://maven.octo-studios.com/releases/")
    }
}

dependencies {
    configurations.getByName("common")(
        project(path = ":Common", configuration = "namedElements")
    ) { isTransitive = false }

    configurations.getByName("shadowCommon")(
        project(path = ":Common", configuration = "transformProductionNeoForge")
    ) { isTransitive = false }

    neoForge(libs.neoforge.neoforge)

    project.extensions.getByType<VersionCatalogsExtension>()
        .named("libs")
        .findLibrary("bettermodsbutton.neoforge")
        .takeIf { it.isPresent }
        ?.get()
        ?.let { lib ->
            modLocalRuntime(lib) { isTransitive = false }
        }
}

tasks.withType<Jar>().configureEach {
    exclude("architectury.common.json")
}

tasks.named<com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar>("shadowJar") {
    configurations = listOf(project.configurations.getByName("shadowCommon"))
    archiveClassifier.set("dev-shadow")
}

tasks.named<net.fabricmc.loom.task.RemapJarTask>("remapJar") {
    from(
        tasks.named<com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar>("shadowJar")
            .flatMap { it.archiveFile }
    )
    dependsOn(tasks.named("shadowJar"))
    archiveClassifier.set("")
    atAccessWideners.add("${project.property("modId")}.accesswidener")
}

tasks.named<Jar>("sourcesJar") {
    val commonSources = project(":Common").tasks.named<Jar>("sourcesJar")
    dependsOn(commonSources)
    from(commonSources.flatMap { it.archiveFile }.map { zipTree(it) })
}

tasks.named("modrinth") {
    finalizedBy(tasks.named("refreshUpdateJson"))
}
tasks.named("curseforge") {
    finalizedBy(tasks.named("refreshUpdateJson"))
}
