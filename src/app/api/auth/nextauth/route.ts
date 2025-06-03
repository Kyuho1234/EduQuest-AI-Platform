import NextAuth from 'next-auth/next';
import CredentialsProvider from 'next-auth/providers/credentials';
import { PrismaClient } from '@prisma/client'; // Prisma Client로 DB 접근
import bcrypt from 'bcrypt'; // 비밀번호 암호화 비교용

const prisma = new PrismaClient(); // Prisma 인스턴스 생성

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: "이메일", type: "email", placeholder: "test@example.com" },
        password: { label: "비밀번호", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          throw new Error('이메일과 비밀번호를 모두 입력하세요.');
        }

        // 1. DB에서 사용자 찾기
        const user = await prisma.user.findUnique({
          where: { email: credentials.email },
        });

        if (!user) {
          throw new Error('존재하지 않는 이메일입니다.');
        }

        // 2. 비밀번호 비교 (입력된 비밀번호 vs 저장된 암호화 비밀번호)
        const isValidPassword = await bcrypt.compare(credentials.password, user.password);
        if (!isValidPassword) {
          throw new Error('비밀번호가 일치하지 않습니다.');
        }

        // 3. 로그인 성공: 세션에 저장할 유저 정보 반환
        return {
          id: user.id.toString(), // NextAuth는 id를 문자열로 요구할 수도 있음
          email: user.email,
          name: user.name,
        };
      }
    })
  ],

  // 추가 설정
  secret: process.env.NEXTAUTH_SECRET,  // JWT 서명용 비밀 키

  session: {
    strategy: 'jwt',  // 세션 대신 JWT 사용
  },

  jwt: {
    secret: process.env.NEXTAUTH_SECRET,  // JWT 토큰 서명 비밀 키
  },

  pages: {
    signIn: '/auth/signin',  // 로그인 실패시 리다이렉트될 페이지
    signOut: '/auth/signin',
  },

  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id as string;  // 로그인 성공하면 token에 id 저장
        token.email = user.email as string;
      }
      return token;
    },
    async session({ session, token }) {
      if (token && session.user) {
        session.user.id = token.id;  // 세션 만들 때 user에 id 심어주기
        session.user.email = token.email;
      }
      return session;
    },
  },
});

export { handler as GET, handler as POST };