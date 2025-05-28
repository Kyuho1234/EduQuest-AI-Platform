'use client';

import { Button } from '@chakra-ui/react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';

export default function MyQuestionsButton() {
  const router = useRouter();
  const { data: session } = useSession();

  const handleClick = () => {
    if (!session) {
      router.push('/auth/signin');
      return;
    }
    router.push('/my-questions');
  };

  return (
    <Button
      onClick={handleClick}
      colorScheme="teal"
      variant="outline"
      size="lg"
    >
      내 문제 보기
    </Button>
  );
}