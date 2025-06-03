'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Container, VStack, Spinner, Center } from '@chakra-ui/react';
import QuizSection from '@/components/QuizSection';

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

export default function SolveClientPage() {
  const searchParams = useSearchParams();
  const [questions, setQuestions] = useState<Question[]>([]);

  useEffect(() => {
    const data = searchParams.get('data');
    if (data) {
      try {
        const parsed = JSON.parse(decodeURIComponent(data));
        setQuestions(parsed);
      } catch (err) {
        console.error('문제 데이터 파싱 오류:', err);
      }
    }
  }, [searchParams]);

  if (questions.length === 0) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="blue.500" />
      </Center>
    );
  }

  return (
    <Container maxW="container.lg" py={10}>
      <VStack spacing={6} align="stretch">
        <QuizSection questions={questions} showSaveButton={false} />
      </VStack>
    </Container>
  );
}
