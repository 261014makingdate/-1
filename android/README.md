# 말모아 Android

Android 7.0(API 24) 이상 64비트 ARM 휴대폰 및 x86_64 에뮬레이터용 앱입니다.
설치는 [설치 안내](INSTALL.txt)를 참고하세요. 번역에는 인터넷 연결이 필요합니다.

JDK 17, Python 3.12, Android SDK Platform 35 / Build Tools 35.0.0이 필요합니다.
Android Studio에서 이 폴더를 열거나 SDK를 `ANDROID_HOME`으로 지정하세요.

저장소 루트에서:

```sh
python -m venv android/.venv-build
android/.venv-build/bin/python android/prepare_wheels.py
cd android
./gradlew assembleDebug assembleDebugAndroidTest lintDebug
./gradlew connectedDebugAndroidTest
```

Windows는 `.venv-build\Scripts\python.exe`와 `gradlew.bat`를 사용합니다.
Gradle 실행 환경에서도 Python 3.12를 찾을 수 있어야 합니다.
결과: `app/build/outputs/apk/debug/app-debug.apk`.

Java 네이티브 화면과 Chaquopy Python 런타임을 사용합니다. Gradle이 공유
`translator` 패키지에서 core/providers/pronunciation 모듈만 복사하며 Qt는 포함하지 않습니다.
순수 Python wrapt, 일본어 사전 경로 호환 처리, Android용 IANA 시간대 데이터를 사용합니다.
기존 테스트와 `tests/test_android_bridge.py`는 호스트에서, `EmbeddedEngineTest`는
Android에서 내장 6개 언어 사전과 입력 오류 처리를 검사합니다.

GitHub Actions `Android APK`는 전용 `android-apk-delivery` 브랜치에 변경이 올라오면
검사와 APK 빌드 후 `android-v0.3.0` 테스트 릴리스로 게시합니다.
태그가 이미 존재하면 새 릴리스를 덮어쓰지 않고 게시 단계가 실패합니다.
개발용 서명이며 스토어 출시에는 소유자가 관리하는 릴리스 서명 키와 별도 절차가 필요합니다.

입력 내용은 번역을 위해 Google 또는 MyMemory에 전송됩니다. 앱은 별도 번역 이력을
저장하지 않으며 화면 복원을 위해 OS가 입력과 결과를 일시 보관할 수 있습니다.
클립보드 복사와 TTS 엔진도 텍스트를 처리하며 TTS는 설정에 따라 네트워크를 사용합니다.
필요 HTTPS 도메인은 translate.googleapis.com, translate.google.com,
api.mymemory.translated.net입니다. TLS 검증은 유지합니다.
