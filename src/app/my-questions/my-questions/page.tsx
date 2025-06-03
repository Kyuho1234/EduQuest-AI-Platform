'use client';

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import {
  Box,
  VStack,
  Heading,
  Text,
  Spinner,
  Center,
  Container,
  Button,
  HStack,
} from '@chakra-ui/react';
import axios from 'axios';
import { useRouter } from 'next/navigation';

interface Question {
  id: string | number;
  question: string;
  correct_answer: string;
  explanation: string;
  options?: string[];
  type: 'multiple_choice' | 'short_answer' | string;
  final_confidence?: number;
  document_name?: string;
}

export default function QuestionsPage() {
  const { data: session, status } = useSession();
  const [groupedQuestions, setGroupedQuestions] = useState<{ [key: string]: Question[] }>({});
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    if (status === 'unauthenticated') {
      window.location.href = '/auth/signin';
      return;
    }

    if (status === 'authenticated' && session?.user?.id) {
      const fetchGrouped = async () => {
        try {
          const res = await axios.get(`http://localhost:8000/api/get-questions/${session.user.id}`);
          setGroupedQuestions(res.data.grouped_questions);
        } catch (err) {
          console.error('문제 그룹 조회 실패:', err);
        } finally {
          setLoading(false);
        }
      };

      fetchGrouped();
    }
  }, [status, session]);

  const handleSolve = (questions: Question[]) => {
    const encoded = encodeURIComponent(JSON.stringify(questions));
    router.push(`/my-questions/solve?data=${encoded}`);
  };

  if (loading || status === 'loading' || !session) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="blue.500" />
      </Center>
    );
  }

  return (
    <Container maxW="container.lg" py={10}>
      <VStack spacing={6} align="stretch">
        <Heading size="lg"> 문제 목록</Heading>
        {Object.entries(groupedQuestions).length === 0 ? (
          <Text>아직 생성된 문제가 없습니다.</Text>
        ) : (
          Object.entries(groupedQuestions).map(([documentName, questions], idx) => (
            <Box key={idx} p={4} borderWidth="1px" borderRadius="md">
              <HStack justify="space-between" align="center">
                <Text fontWeight="bold">학습자료: {documentName}</Text>
                <Button colorScheme="teal" onClick={() => handleSolve(questions)}>
                  문제풀기
                </Button>
              </HStack>
            </Box>
          ))
        )}
      </VStack>
    </Container>
  );
}