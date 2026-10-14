# 말모아 — 한국어 PC 번역기

Python 3.12+ / PySide6로 만든 데스크톱 앱입니다. 한국어 입력 → 언어 선택 → **번역하기**를 누르면 번역과 발음이 표시됩니다. 중국어, 일본어, 영어, 태국어, 라오스어, 러시아어를 지원합니다.

## 실행

```sh
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m translator
```

macOS / Linux:

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m translator
```

Linux에서는 그래픽 데스크톱 및 Qt 시스템 라이브러리가 필요합니다. 화면 없는 CI 환경의 검증은 `QT_QPA_PLATFORM=offscreen`을 사용합니다.

## 발음과 번역 서비스

발음은 서비스의 로마자 표기를 우선 사용합니다. 없으면 중국어 병음, 일본어 로마자, 영어 IPA, 나머지 언어의 간이 로마자 표기를 제공합니다. 한글 독음이나 음성 재생 기능은 포함하지 않습니다. 태국어·라오스어의 간이 표기는 실제 발음과 성조를 정확히 표현하지 못할 수 있으며 화면에 안내됩니다.

인터넷 연결이 필요하며 입력 내용은 Google 또는 보조 번역 서비스 MyMemory 서버로 전송됩니다. Google은 API 키 없이 이용하는 **비공식 웹 엔드포인트**를 사용하므로 서비스 변경이나 요청 제한으로 실패할 수 있습니다. 배포·상용 운영 시 공식 번역 API로 `TranslationProvider` 구현을 교체하는 것을 권장합니다. Google 요청이 실패하면 [MyMemory 공개 API](https://mymemory.translated.net/doc/spec.php)를 이용합니다. MyMemory는 무료 사용량 제한이 있고, 긴 문장은 요청당 450자로 나누어 번역하므로 문맥 정확도가 낮아질 수 있습니다. API 키를 사용하는 공식 서비스로 교체할 때는 비밀키를 앱에 포함하지 말고 서버에서 관리하세요. 번역 실패 시 오류를 표시하며 이전 결과는 지웁니다.

## 구조

- `translator/core.py`: 언어, 결과, 서비스 인터페이스와 입력 검증
- `translator/providers.py`: 외부 번역 요청 및 발음 변환
- `translator/ui.py`: PC 화면 및 별도 스레드에서의 번역 처리
- `translator/__main__.py`: 의존성 조립과 실행

서비스는 생성자로 주입합니다. UI는 네트워크 구현을 알 필요가 없고, 공급자를 교체하거나 테스트용 구현을 사용할 수 있습니다. 서버별 연결 대기는 6초, 응답 대기는 12초로 제한합니다. 첫 서버 요청이 실패하면 Google 웹 번역 도메인으로 다시 요청하며, API 요청 제한 시 일반 웹 번역 경로도 사용합니다. Windows에서는 시스템의 신뢰 인증서와 수동 프록시 설정을 사용합니다.

## 테스트

```sh
.venv/bin/python -m pip install pytest
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Windows에서는 `.venv\Scripts\python -m pytest -q`를 사용합니다.

## Windows 실행 파일

GitHub 배포 파일은 [v0.1.0 릴리스](https://github.com/261014makingdate/-1/releases/tag/v0.1.0)에서 찾을 수 있습니다. [Malmoa.exe 다운로드](https://github.com/261014makingdate/-1/releases/download/v0.1.0/Malmoa.exe) 또는 [ZIP 다운로드](https://github.com/261014makingdate/-1/releases/download/v0.1.0/Malmoa-Windows-x64.zip)를 선택하세요.

`dist/Malmoa.exe`를 Windows 10/11 64비트 PC에 복사하고 더블 클릭하세요. Python을 별도로 설치할 필요가 없습니다. 단일 실행 파일이며 번역에는 인터넷 연결이 필요합니다. 최초 실행 시 내부 파일을 임시 폴더에 풀기 때문에 잠시 걸릴 수 있습니다.

Windows용 Python 3.12.10, Qt 6.8.3, PyInstaller 6.22.3으로 빌드했습니다. Windows 바이너리 형식(PE32+, x64, GUI)을 확인했고 Wine 10에서 테스트 13개 및 생성된 실행 파일의 오프라인 진단이 통과했습니다. 진단은 화면, 작업 스레드, 번역 결과 표시와 6개 언어 발음 데이터 포함 여부를 확인합니다. GitHub 배포 빌드는 [Windows Actions 실행](https://github.com/261014makingdate/-1/actions/runs/38502152350)에서도 테스트와 실행 파일의 오프라인 진단을 통과했습니다. v0.1.1부터는 실행 파일을 통한 6개 언어의 실제 번역과 발음 검사도 모두 통과해야 게시합니다. Windows에서 번역이 실패하면 TLS·PROXY·CONNECT·HTTP·TIMEOUT·RESPONSE 오류 코드로 원인을 구분할 수 있습니다.

검사 결과는 `dist/self-test.json`, 파일 해시는 `dist/Malmoa.exe.sha256`에 있습니다. 실행 파일의 오프라인 진단은 다음처럼 실행할 수 있습니다.

```powershell
$p = Start-Process -FilePath .\dist\Malmoa.exe -ArgumentList '--self-test', 'self-test.json' -Wait -PassThru
Get-Content -Encoding UTF8 self-test.json
```

## Windows에서 다시 빌드

Windows 64비트 Python 3.12와 Python 런처(`py`)를 설치한 후 저장소 루트에서 다음을 실행하세요.

```powershell
powershell -File packaging\build-windows.ps1
```

스크립트는 전용 `.venv-windows` 환경을 만들고, `packaging/requirements-windows.txt`의 고정된 버전을 설치하고, `dist/Malmoa.exe`를 빌드한 뒤 실행 파일 자체의 오프라인 진단을 확인합니다. 화면 구성에 필요한 Qt Essentials만 포함합니다. 코드 서명은 적용하지 않았습니다.

## GitHub 자동 배포

`v*` 태그를 게시하면 `.github/workflows/windows-release.yml`이 Windows에서 테스트, 실행 파일 빌드 및 오프라인 진단을 실행합니다. 실행 파일을 통한 6개 언어의 실제 번역·발음 검사까지 모두 통과한 뒤 실행 파일과 ZIP을 GitHub Releases에 첨부합니다. 진행 상황은 저장소의 Actions에서 확인할 수 있습니다.
