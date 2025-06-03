'use client';

import { Button, useToast } from '@chakra-ui/react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import axios from 'axios';

export default function MyQuestionsButton() {
  const { data: session } = useSession();
  const router = useRouter();
  const toast = useToast();

  const handleViewMyQuestions = async () => {
    if (!session?.user?.email) {
      toast({
        title: '로그인이 필요합니다.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    router.push('/my-questions'); // 미리 만든 페이지로 이동
  };

  return (
      <Button colorScheme="teal" onClick={handleViewMyQuestions}>
        내 문제 보기
      </Button>
  );
}
