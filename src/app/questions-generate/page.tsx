'use client';

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import {
  Container,
  VStack,
  Spinner,
  Center,
  Heading,
  useToast,
  Text,
} from '@chakra-ui/react';

import PDFUploader from '@/components/PDFUploader';
import DocumentSelector from '@/components/DocumentSelector';
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

export default function Home() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [documentName, setDocumentName] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.replace('/auth/signin');
    }
  }, [status, router]);

  if (status === 'loading' || !session) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="blue.500" />
      </Center>
    );
  }

  const handleDocumentSelected = async (documentId: string, documentName: string) => {
    setIsGenerating(true);
    try {
      const res = await fetch('https://edubackend-production.up.railway.app/api/generate-questions-from-document', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: documentId, user_id: session.user.id }),
      });
      const data = await res.json();
      const enrichedQuestions = (data.questions || []).map((q: any) => ({
        ...q,
        document_name: documentName,
      }));

      setQuestions(enrichedQuestions);
      setDocumentName(documentName);
      if (data.questions?.length === 0) {
        toast({
          title: '문제 없음',
          description: '이 문서에서는 유효한 문제가 생성되지 않았습니다.',
          status: 'warning',
          duration: 3000,
          isClosable: true,
        });
      }
    } catch (error) {
      toast({
        title: '문제 생성 실패',
        description: '서버에서 문제 생성 중 오류가 발생했습니다.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Container maxW="container.lg" py={10}>
      <VStack spacing={8} align="stretch">
        {isGenerating ? (
          <Center h="200px" flexDir="column">
            <Spinner size="lg" color="blue.500" mb={4} />
            <Text fontSize="lg">문제 생성 중입니다...</Text>
          </Center>
        ) : questions.length === 0 ? (
          <>
            <Heading size="lg">문제 생성</Heading>
            <PDFUploader
              onUploadComplete={(docId) => {
                setRefreshKey(prev => prev + 1);
                toast({
                  title: '업로드 성공',
                  description: '문서가 업로드되었습니다. 아래에서 선택하여 문제를 생성하세요.',
                  status: 'success',
                  duration: 3000,
                  isClosable: true,
                });
              }}
            />
            <DocumentSelector
              userId={session.user.id}
              onSelect={handleDocumentSelected}
              refreshTrigger={refreshKey}
            />
          </>
        ) : (
          <>
            <Heading size="lg">{documentName}</Heading>
            <QuizSection questions={questions} />
          </>
        )}
      </VStack>
    </Container>
  );
}