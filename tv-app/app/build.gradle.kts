plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "dev.openkaraoke.stage"
    compileSdk = 36

    defaultConfig {
        applicationId = "dev.openkaraoke.stage"
        minSdk = 30
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.core.ktx)
}
