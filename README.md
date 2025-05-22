# EduQuest

EduQuest는 인공지능을 활용한 교육용 문제 생성 및 학습 지원 시스템입니다. 텍스트나 PDF 문서를 기반으로 문제를 자동 생성하고, RAG(Retrieval-Augmented Generation)를 활용하여 정확한 학습 지원을 제공합니다.

## 주요 기능

- **문서 기반 문제 생성**: PDF 문서를 업로드하면 AI가 자동으로 문제를 생성합니다.
- **RAG 기반 검증**: 생성된 문제가 입력 자료와 일치하는지 검증합니다.
- **채점 및 피드백**: 학습자의 답변을 채점하고 개인화된 피드백을 제공합니다.
- **사용자 인증**: 안전한 로그인 시스템을 통해 개인 학습 데이터를 관리합니다.

## 기술 스택

### 프론트엔드
- Next.js
- React
- NextAuth (인증)
- Prisma (ORM)

### 백엔드
- FastAPI (Python)
- Google Gemini API
- RAG (Retrieval-Augmented Generation)
- PostgreSQL

## 설치 방법

### 프론트엔드 설치

```bash
# 저장소 복제
git clone https://github.com/yourusername/EduQuest.git
cd EduQuest

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

### 백엔드 설치

```bash
# 백엔드 디렉토리로 이동
cd backend

# 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python main.py
```

## 환경 변수 설정

### 프론트엔드 환경 변수 (.env.local)

```
# 데이터베이스 연결 정보
DATABASE_URL="postgresql://user:password@localhost:5432/eduquest"

# 인증 관련
NEXTAUTH_SECRET="your-nextauth-secret-key"
NEXTAUTH_URL="http://localhost:3000"

# API 키
GOOGLE_API_KEY="your-google-api-key"
```

### 백엔드 환경 변수 (backend/.env)

```
# API 키
GOOGLE_API_KEY="your-google-api-key"
OPENROUTER_API_KEY="your-openrouter-api-key"

# 데이터베이스 연결 정보
DB1_URL="postgresql://db1_user:db1_pass@localhost:5432/db1_database"
DB2_URL="postgresql://db2_user:db2_pass@localhost:5432/db2_database"
```

## 브랜치 구조

- `main`: 안정화된 배포용 코드
- `develop`: 개발 중인 코드
- `frontend`: 프론트엔드 관련 기능
- `backend`: 백엔드 관련 기능
- `auth`: 인증 시스템
- `rag`: RAG 기능
- `question-generation`: 문제 생성 기능

## 라이선스

MIT License 