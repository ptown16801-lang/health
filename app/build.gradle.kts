plugins {
    id("com.android.application")
}

android {
    namespace = "com.jefferson.health"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.jefferson.health"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"

        testInstrumentationRunner = "android.support.test.runner.AndroidJUnitRunner"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/controlledCorpus"))
}

val generateControlledCorpus by tasks.registering(Exec::class) {
    val output = layout.buildDirectory.dir("generated/controlledCorpus/controlled-corpus")
    inputs.files(
        rootProject.fileTree("fixtures"),
        rootProject.fileTree("tests/data"),
        rootProject.fileTree("health_ingest"),
        rootProject.fileTree("scripts"),
    )
    outputs.dir(output)
    workingDir(rootProject.projectDir)
    commandLine("python3", "-m", "scripts.build_android_corpus", "--output", output.get().asFile)
}

tasks.named("preBuild").configure { dependsOn(generateControlledCorpus) }

dependencies {
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("com.android.support.test:runner:1.0.2")
    androidTestImplementation("com.android.support.test:rules:1.0.2")
}
