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

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    testOptions.unitTests.isIncludeAndroidResources = true

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
    testImplementation("org.robolectric:robolectric:4.14.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:rules:1.6.1")
}
