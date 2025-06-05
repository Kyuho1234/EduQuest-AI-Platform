'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  Radio,
  RadioGroup,
  Stack,
  Text,
  Progress,
  Textarea,
  VStack,
  Heading,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Center,
  useToast,
  HStack,
  Spinner,
} from '@chakra-ui/react';
import axios, { AxiosError } from 'axios';
import { useSession } from 'next-auth/react';

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

interface QuizSectionProps {
  questions: Question[];
  showSaveButton?: boolean;
  onQuizReset?: () => void;
}

interface QuizResultItemAPI {
  question_id?: string | number;
  is_correct: boolean;
  feedback: string;
  question: string;
  user_answer: string;
  correct_answer: string;
  explanation?: string;
}

interface CheckAnswersApiResponse {
  total: {
    total_score: number;
    total_questions: number;
    score_percentage: number;
    overall_feedback: string;
  };
  results: QuizResultItemAPI[];
}

export default function QuizSection({ questions, showSaveButton = true, onQuizReset }: QuizSectionProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<string[]>(() => new Array(questions.length).fill(''));
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [quizEvalResults, setQuizEvalResults] = useState<CheckAnswersApiResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const toast = useToast();

  const { data: session } = useSession();

  useEffect(() => {
    setAnswers(new Array(questions.length).fill(''));
    setCurrentIndex(0);
    setSubmitted(false);
    setQuizEvalResults(null);
    setApiError(null);
    setLoading(false);
  }, [questions]);

  const currentQuestion = questions && questions.length > 0 ? questions[currentIndex] : null;
  const progress = questions.length > 0 ? ((currentIndex + 1) / questions.length) * 100 : 0;

  const handleAnswerChange = (value: string) => {
    const newAnswers = [...answers];
    newAnswers[currentIndex] = value;
    setAnswers(newAnswers);
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const handleSubmitAll = async () => {
    const emptyAnswers = answers.some(answer => !answer.trim());
    if (emptyAnswers) {
      toast({
        title: '모든 문제에 답해주세요.',
        status: 'warning',
        duration: 3000,
        isClosable: true,
        position: "top"
      });
      return;
    }
    if (questions.length === 0) {
      toast({ title: "제출할 문제가 없습니다.", status: "info", duration: 2000, position: "top"});
      return;
    }

    setLoading(true);
    setApiError(null);
    try {
      const answersData = questions.map((question, index) => ({
        question_id: question.id || `q-idx-${index}`,
        question: question.question,
        user_answer: answers[index],
        correct_answer: question.correct_answer,
        explanation: question.explanation,
        options: question.options,
        type: question.type,
      }));

      const response = await axios.post<CheckAnswersApiResponse>(
          'https://edubackend-production.up.railway.app/api/check-answers',
          { answers: answersData }
      );

      if (response.data && response.data.total && typeof response.data.total.score_percentage === 'number') {
        setQuizEvalResults(response.data);
        toast({ title: "채점이 완료되었습니다!", status: "success", duration: 2000, position: "top" });
      } else {
        const errorMessage = "결과 데이터 형식이 올바르지 않습니다.";
        setApiError(errorMessage);
        toast({
          title: '결과 처리 오류',
          description: errorMessage,
          status: 'error',
          duration: 7000,
          isClosable: true,
          position: "top"
        });
        setQuizEvalResults(response.data);
      }
      setSubmitted(true);

    } catch (error) {
      let errorDesc = '답변 제출 중 서버와 통신에 실패했습니다. 잠시 후 다시 시도해주세요.';
      if (axios.isAxiosError(error)) {
        if (error.response) {
          errorDesc = error.response.data?.detail || error.response.data?.error || error.message;
        } else {
          errorDesc = error.message;
        }
      }
      setApiError(errorDesc);
      toast({
        title: '제출 중 오류 발생',
        description: errorDesc,
        status: 'error',
        duration: 7000,
        isClosable: true,
        position: "top"
      });
      setQuizEvalResults(null);
      setSubmitted(true);
    } finally {
      setLoading(false);
    }
  };

  const saveQuestions = async () => {
    if (!session?.user?.id) {
      toast({ title: '로그인이 필요합니다.', status: 'error', position: "top" });
      return;
    }

    try {
      await axios.post('https://edubackend-production.up.railway.app/api/save-questions', {
        user_id: session.user.id,
        questions
      });
      toast({ title: '문제가 저장되었습니다!', status: 'success', duration: 2000, position: "top"});
    } catch (error) {
      console.error('문제 저장 실패:', error);
      toast({ title: '문제 저장 중 오류가 발생했습니다.', status: 'error', position: "top" });
    }
  };

  const handleReset = () => {
    setAnswers(new Array(questions.length).fill(''));
    setCurrentIndex(0);
    setSubmitted(false);
    setQuizEvalResults(null);
    setApiError(null);
    setLoading(false);
    
    if (onQuizReset) {
      onQuizReset();
    }
  };

  if (loading) {
    return (
      <Center h="300px" flexDirection="column">
        <Spinner size="lg" color="blue.500" mb={4} />
        <Text fontSize="lg">답안을 채점 중입니다...</Text>
      </Center>
    );
  }

  if (submitted) {
    if (apiError && !quizEvalResults) {
      return (
        <VStack spacing={6} p={6}>
          <Alert status="error">
            <AlertIcon />
            <Box>
              <AlertTitle>채점 중 오류 발생!</AlertTitle>
              <AlertDescription>{apiError}</AlertDescription>
            </Box>
          </Alert>
          <Button colorScheme="teal" onClick={handleReset}>
            다시 시도
          </Button>
        </VStack>
      );
    }

    if (quizEvalResults && quizEvalResults.total) {
      return (
        <VStack spacing={6} p={6}>
          <Heading size="lg">📊 퀴즈 결과</Heading>
          
          <Box textAlign="center" p={6} borderWidth="1px" borderRadius="lg" bg="blue.50">
            <Text fontSize="2xl" fontWeight="bold" color="blue.600">
              {quizEvalResults.total.score_percentage.toFixed(1)}%
            </Text>
            <Text fontSize="lg">
              {quizEvalResults.total.total_score} / {quizEvalResults.total.total_questions} 정답
            </Text>
            <Text mt={2} color="gray.600">
              {quizEvalResults.total.overall_feedback}
            </Text>
          </Box>

          {apiError && (
            <Alert status="warning">
              <AlertIcon />
              <AlertDescription>{apiError}</AlertDescription>
            </Alert>
          )}

          <VStack spacing={4} align="stretch" w="100%">
            {quizEvalResults.results && quizEvalResults.results.length > 0 ? (
              quizEvalResults.results.map((result, index) => (
                <Box key={index} p={4} borderWidth="1px" borderRadius="md" 
                     bg={result.is_correct ? "green.50" : "red.50"}>
                  <Text fontWeight="bold" mb={2}>
                    문제 {index + 1}: {result.is_correct ? "✅ 정답" : "❌ 오답"}
                  </Text>
                  <Text mb={1}><strong>문제:</strong> {result.question}</Text>
                  <Text mb={1}><strong>내 답안:</strong> {result.user_answer}</Text>
                  <Text mb={1}><strong>정답:</strong> {result.correct_answer}</Text>
                  {result.explanation && (
                    <Text mb={1}><strong>설명:</strong> {result.explanation}</Text>
                  )}
                  <Text color="gray.600"><strong>피드백:</strong> {result.feedback}</Text>
                </Box>
              ))
            ) : (
              <Text>개별 문제 결과를 불러올 수 없습니다.</Text>
            )}
          </VStack>

          <HStack spacing={4}>
            <Button colorScheme="teal" onClick={handleReset}>
              다시 풀기
            </Button>
            {showSaveButton && (
              <Button colorScheme="blue" onClick={saveQuestions}>
                문제 저장
              </Button>
            )}
          </HStack>
        </VStack>
      );
    }

    return (
      <VStack spacing={6} p={6}>
        <Alert status="error">
          <AlertIcon />
          <Box>
            <AlertTitle>결과를 표시할 수 없습니다!</AlertTitle>
            <AlertDescription>
              서버 응답 형식이 예상과 다릅니다. 관리자에게 문의하세요.
              {apiError && ` (${apiError})`}
            </AlertDescription>
          </Box>
        </Alert>
        <Button colorScheme="teal" onClick={handleReset}>
          다시 시도
        </Button>
      </VStack>
    );
  }

  if (!currentQuestion) {
    return (
      <Center h="200px">
        <Text fontSize="lg" color="gray.500">문제가 없습니다.</Text>
      </Center>
    );
  }

  return (
    <VStack spacing={6} w="100%">
      <Progress value={progress} w="100%" colorScheme="blue" size="lg" />
      
      <Box textAlign="center">
        <Text fontSize="sm" color="gray.500">
          문제 {currentIndex + 1} / {questions.length}
        </Text>
      </Box>

      <Box p={6} borderWidth="1px" borderRadius="lg" w="100%">
        <Text fontSize="lg" fontWeight="bold" mb={4}>
          {currentQuestion.question}
        </Text>

        {currentQuestion.type === 'multiple_choice' && currentQuestion.options ? (
          <RadioGroup value={answers[currentIndex]} onChange={handleAnswerChange}>
            <Stack spacing={3}>
              {currentQuestion.options.map((option, idx) => (
                <Radio key={idx} value={option}>
                  {option}
                </Radio>
              ))}
            </Stack>
          </RadioGroup>
        ) : (
          <Textarea
            placeholder="답안을 입력하세요..."
            value={answers[currentIndex]}
            onChange={(e) => handleAnswerChange(e.target.value)}
            rows={4}
          />
        )}
      </Box>

      <HStack spacing={4} w="100%" justify="space-between">
        <Button
          onClick={handlePrevious}
          isDisabled={currentIndex === 0}
          variant="outline"
        >
          이전
        </Button>

        <HStack spacing={2}>
          {currentIndex < questions.length - 1 ? (
            <Button onClick={handleNext} colorScheme="blue">
              다음
            </Button>
          ) : (
            <Button onClick={handleSubmitAll} colorScheme="green" size="lg">
              제출하기
            </Button>
          )}
        </HStack>
      </HStack>

      {showSaveButton && (
        <Button colorScheme="teal" variant="outline" onClick={saveQuestions}>
          문제 저장
        </Button>
      )}
    </VStack>
  );
}