'use client';

import React, { useState } from 'react';
import {
  Box,
  Button,
  Radio,
  RadioGroup,
  Stack,
  Text,
  Progress,
  Input,
  VStack,
  Heading,
  Alert,
  AlertTitle,
  AlertDescription,
  useToast,
} from '@chakra-ui/react';
import axios from 'axios';
import { useSession } from 'next-auth/react';

interface Question {
  question: string;
  correct_answer: string;
  explanation: string;
  options?: string[];
  type: 'multiple_choice' | 'short_answer';
}

interface QuizSectionProps {
  questions: Question[];
  showSaveButton?: boolean;
}

interface QuizResult {
  is_correct: boolean;
  feedback: string;
  question: string;
  user_answer: string;
  correct_answer: string;
}

interface QuizResults {
  total: {
    total_score: number;
    total_questions: number;
    score_percentage: number;
    overall_feedback: string;
  };
  results: QuizResult[];
}

export default function QuizSection({ questions, showSaveButton = true }: QuizSectionProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<string[]>(new Array(questions.length).fill(''));
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<QuizResults | null>(null);
  const toast = useToast();

  const currentQuestion = questions[currentIndex];
  const progress = ((currentIndex + 1) / questions.length) * 100;

  const { data: session } = useSession();

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
      });
      return;
    }

    try {
      setLoading(true);

      const answersData = questions.map((question, index) => ({
        question: question.question,
        user_answer: answers[index],
        correct_answer: question.correct_answer,
        question_type: question.type,
      }));

      const response = await axios.post<QuizResults>('http://localhost:8000/api/check-answers', {
        answers: answersData,
      });

      setResults(response.data);
      setSubmitted(true);
    } catch (error) {
      console.error('Error submitting answers:', error);
      toast({
        title: '제출 중 오류가 발생했습니다.',
        description: '잠시 후 다시 시도해주세요.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveQuestions = async () => {
    try {
      if (!session?.user?.id) {
        throw new Error('로그인 정보가 없습니다.');
      }
      await axios.post('http://localhost:8000/api/save-questions', {
        user_id: session.user.id,
        questions: questions,
      });

      toast({
        title: '문제 저장 완료!',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error('문제 저장 실패:', error);
      toast({
        title: '문제 저장 실패',
        description: '잠시 후 다시 시도해주세요.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleReset = () => {
    setCurrentIndex(0);
    setAnswers(new Array(questions.length).fill(''));
    setSubmitted(false);
    setResults(null);
  };

  if (submitted && results) {
    return (
        <VStack spacing={6} align="stretch" w="100%" p={4}>
          <Heading size="lg">퀴즈 결과</Heading>

          <Alert
              status={results.total.score_percentage >= 70 ? 'success' : 'warning'}
              variant="subtle"
              flexDirection="column"
              alignItems="flex-start"
              p={4}
              borderRadius="md"
          >
            {results?.total?.score_percentage !== undefined && (
                <>
                  <AlertTitle mb={2}>
                    점수: {results.total.score_percentage.toFixed(1)}% ({results.total.total_score}/{results.total.total_questions})
                  </AlertTitle>
                  <AlertDescription whiteSpace="pre-wrap">
                    {results.total.overall_feedback}
                  </AlertDescription>
                </>
            )}
          </Alert>

          <VStack spacing={4} align="stretch">
            {results.results.map((result, index) => (
                <Box key={index} p={4} borderWidth={1} borderRadius="md">
                  <Text fontWeight="bold" mb={2}>
                    문제 {index + 1}: {result.question}
                  </Text>
                  <Text color={result.is_correct ? 'green.500' : 'red.500'} mb={2}>
                    내 답변: {result.user_answer}
                  </Text>
                  <Text color="gray.600" mb={2}>
                    정답: {result.correct_answer}
                  </Text>
                  <Text whiteSpace="pre-wrap">{result.feedback}</Text>
                </Box>
            ))}
          </VStack>

          <Stack direction="row" spacing={4}>
            <Button onClick={handleReset} colorScheme="blue">
              다시 풀기
            </Button>
          </Stack>
        </VStack>
    );
  }

  return (
      <VStack spacing={6} align="stretch" w="100%" p={4}>
        <Box>
          <Text mb={2}>문제 {currentIndex + 1} / {questions.length}</Text>
          <Progress value={progress} colorScheme="blue" borderRadius="md" />
        </Box>

        <Box p={6} borderWidth={1} borderRadius="md">
          <Heading size="md" mb={4}>
            {currentQuestion.question}
          </Heading>

          {currentQuestion.type === 'multiple_choice' && currentQuestion.options ? (
              <RadioGroup
                  value={answers[currentIndex]}
                  onChange={handleAnswerChange}
              >
                <Stack spacing={3}>
                  {currentQuestion.options.map((option, index) => (
                      <Radio key={index} value={option}>
                        {option}
                      </Radio>
                  ))}
                </Stack>
              </RadioGroup>
          ) : (
              <Input
                  placeholder="답을 입력하세요"
                  value={answers[currentIndex]}
                  onChange={(e) => handleAnswerChange(e.target.value)}
              />
          )}
        </Box>

        <Stack direction="row" spacing={4} justify="space-between">
          <Button
              onClick={handlePrevious}
              isDisabled={currentIndex === 0}
              variant="outline"
          >
            이전
          </Button>

          <Stack direction="row" spacing={2}>
            {showSaveButton && (
                <Button onClick={handleSaveQuestions} colorScheme="green" variant="outline">
                  문제 저장
                </Button>
            )}

            {currentIndex === questions.length - 1 ? (
                <Button
                    onClick={handleSubmitAll}
                    colorScheme="blue"
                    isLoading={loading}
                    loadingText="채점 중..."
                >
                  제출하기
                </Button>
            ) : (
                <Button
                    onClick={handleNext}
                    colorScheme="blue"
                    isDisabled={currentIndex === questions.length - 1}
                >
                  다음
                </Button>
            )}
          </Stack>
        </Stack>
      </VStack>
  );
}