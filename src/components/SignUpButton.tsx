'use client';

import React, { useState } from 'react';
import { Button, Input, VStack, FormControl, FormLabel, useToast } from '@chakra-ui/react';
import { signIn } from 'next-auth/react';

export default function SignUpButton() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const toast = useToast();

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const response = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, name }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error);
      }

      toast({
        title: '회원가입 성공',
        description: '자동으로 로그인됩니다.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      // 회원가입 성공 후 자동 로그인
      await signIn('credentials', {
        email,
        password,
        redirect: true,
      });
    } catch (error: any) {
      toast({
        title: '회원가입 실패',
        description: error.message || '회원가입 중 오류가 발생했습니다.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  return (
    <form onSubmit={handleSignUp}>
      <VStack spacing={4} align="stretch">
        <FormControl>
          <FormLabel>이름</FormLabel>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="이름을 입력하세요"
            required
          />
        </FormControl>
        <FormControl>
          <FormLabel>이메일</FormLabel>
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="이메일을 입력하세요"
            required
          />
        </FormControl>
        <FormControl>
          <FormLabel>비밀번호</FormLabel>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="비밀번호를 입력하세요"
            required
          />
        </FormControl>
        <Button type="submit" colorScheme="green">
          회원가입
        </Button>
      </VStack>
    </form>
  );
} 