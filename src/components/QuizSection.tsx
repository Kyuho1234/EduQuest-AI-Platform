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
  Textarea, // Textarea 추가
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
import axios, { AxiosError } from 'axios'; // AxiosError 타입 명시적 import
import { useSession } from 'next-auth/react';

// 프론트엔드에서 사용할 문제 객체 타입
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

// 백엔드 /api/check-answers 응답의 개별 문제 결과 타입
interface QuizResultItemAPI {
  question_id?: string | number;
  is_correct: boolean;
  feedback: string;
  question: string;
  user_answer: string;
  correct_answer: string;
  explanation?: string;
}

// 백엔드 /api/check-answers 응답의 전체 구조 타입
interface CheckAnswersApiResponse {
  total: {
    total_score: number;
    total_questions: number;
    score_percentage: number;
    overall_feedback: string;
  };
  results: QuizResultItemAPI[];
  // 백엔드에서 success 필드를 보내지 않는 것으로 가정했으므로 제거. 필요시 추가.
  // success?: boolean; 
  // error?: string; // 최상위 에러 필드는 axios 에러 처리로 대체 가능
}

export default function QuizSection({ questions, showSaveButton = true, onQuizReset }: QuizSectionProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<string[]>(() => new Array(questions.length).fill(''));
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [quizEvalResults, setQuizEvalResults] = useState<CheckAnswersApiResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null); // API 호출 에러 메시지 저장
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
    setApiError(null); // 이전 에러 메시지 초기화
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

      console.log('Submitting to /api/check-answers, Payload:', JSON.stringify({ answers: answersData }, null, 2));

      const response = await axios.post<CheckAnswersApiResponse>(
          'http://localhost:8000/api/check-answers',
          { answers: answersData }
      );

      // ★★★★★ 실제 백엔드 응답 데이터 구조 확인을 위한 로그 ★★★★★
      console.log('--- API Response Data from /api/check-answers (SUCCESS) ---');
      console.log(JSON.stringify(response.data, null, 2));
      // ★★★★★-------------------------------------------★ ★★★★★

      if (response.data && response.data.total && typeof response.data.total.score_percentage === 'number') {
        setQuizEvalResults(response.data);
        toast({ title: "채점이 완료되었습니다!", status: "success", duration: 2000, position: "top" });
      } else {
        console.error("Backend response format unexpected:", response.data);
        const errorMessage = "결과 데이터 형식이 올바르지 않습니다. (total or score_percentage missing/invalid)";
        setApiError(errorMessage); // 에러 상태에 메시지 저장
        toast({
          title: '결과 처리 오류',
          description: errorMessage,
          status: 'error',
          duration: 7000, // 사용자가 읽을 수 있도록 시간 늘림
          isClosable: true,
          position: "top"
        });
        setQuizEvalResults(response.data); // 형식이 달라도 일단 저장해서 화면에 표시 (디버깅용)
      }
      setSubmitted(true); // 응답을 받았으므로 제출된 것으로 처리 (성공/실패 여부와 관계없이)

    } catch (error) {
      console.error('Error submitting answers (Axios Error):', error);
      let errorDesc = '답변 제출 중 서버와 통신에 실패했습니다. 잠시 후 다시 시도해주세요.';
      if (axios.isAxiosError(error)) {
        if (error.response) {
          console.error('--- Backend Error Response Data (AXIOS) ---');
          console.error(JSON.stringify(error.response.data, null, 2));
          // 백엔드가 보낸 detail 메시지가 있다면 사용
          errorDesc = error.response.data?.detail || error.response.data?.error || error.message;
        } else {
          errorDesc = error.message; // 네트워크 에러 등
        }
      }
      setApiError(errorDesc); // 에러 상태에 메시지 저장
      toast({
        title: '제출 중 오류 발생',
        description: errorDesc,
        status: 'error',
        duration: 7000,
        isClosable: true,
        position: "top"
      });
      setQuizEvalResults(null); // 오류 시 결과는 null로
      setSubmitted(true); // 오류가 발생했음을 알리기 위해 submitted는 true
    } finally {
      setLoading(false);
    }
  };

  const handleSaveQuestions = async () => {
    // ... (이 함수는 이전 답변과 동일하게 유지)
    const questionsToSave = questions.map(q => ({
      question: q.question,
      correct_answer: q.correct_answer,
      explanation: q.explanation,
      options: q.options || [],
      type: q.type,
      document_name: q.document_name || ''
    }));

    try {
      const userIdToSave = session?.user?.id || session?.user?.email;
      if (!userIdToSave) {
        toast({ title: '로그인 정보가 없어 문제를 저장할 수 없습니다.', status: 'error', duration: 3000, position: "top" });
        return;
      }
      setLoading(true);
      await axios.post('http://localhost:8000/api/save-questions', {
        user_id: userIdToSave,
        questions: questionsToSave,
      });
      toast({
        title: '문제 저장 완료!',
        description: `${questionsToSave.length}개의 문제가 성공적으로 저장되었습니다.`,
        status: 'success',
        duration: 3000,
        isClosable: true,
        position: "top"
      });
    } catch (error) {
      console.error('문제 저장 실패:', error);
      toast({ title: '문제 저장 실패', description: '잠시 후 다시 시도해주세요.', status: 'error', duration: 3000, position: "top"});
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setCurrentIndex(0);
    setAnswers(new Array(questions.length).fill(''));
    setSubmitted(false);
    setQuizEvalResults(null);
    setApiError(null);
    setLoading(false);
    if (onQuizReset) onQuizReset();
  };

  // ----- 0. 로딩 중 UI -----
  if (loading) {
    return (
        <Center h="200px">
          <VStack>
            <Spinner thickness="4px" speed="0.65s" emptyColor="gray.200" color="teal.500" size="xl" />
            <Text mt={2}>처리 중입니다...</Text>
          </VStack>
        </Center>
    );
  }

  // ----- 1. 결과 표시 UI -----
  if (submitted) { // submitted가 true이면 결과를 표시하려고 시도
    if (quizEvalResults && quizEvalResults.total && typeof quizEvalResults.total.score_percentage === 'number') {
      // 정상적인 결과 데이터가 있을 때
      const { total, results: individualItems } = quizEvalResults;
      return (
          <VStack spacing={6} align="stretch" w="100%" p={{base: 3, md: 5}} borderWidth="1px" borderRadius="lg" shadow="lg" bg="white">
            <Heading size="xl" textAlign="center" color="gray.700">📊 퀴즈 결과</Heading>
            <Alert
                status={total.score_percentage >= 70 ? 'success' : total.score_percentage >= 40 ? 'warning' : 'error'}
                variant="subtle" flexDirection="column" alignItems="center" justifyContent="center"
                textAlign="center" p={6} borderRadius="md" borderWidth="1px"
                borderColor={total.score_percentage >= 70 ? 'green.300' : total.score_percentage >= 40 ? 'yellow.300' : 'red.300'}
            >
              <AlertIcon boxSize="40px" />
              <AlertTitle mt={3} mb={2} fontSize="2xl" fontWeight="bold">
                총점: {total.score_percentage.toFixed(1)}%
                <Text as="span" fontSize="lg" fontWeight="normal" ml={2}>
                  ({total.total_score} / {total.total_questions} 맞음)
                </Text>
              </AlertTitle>
              {total.overall_feedback && (
                  <AlertDescription whiteSpace="pre-wrap" fontSize="md" color="gray.600">
                    {total.overall_feedback}
                  </AlertDescription>
              )}
            </Alert>

            <VStack spacing={5} align="stretch" mt={4}>
              {individualItems.map((resultItem, index) => (
                  <Box
                      key={resultItem.question_id || `result-item-${index}`}
                      p={5} borderWidth={1} borderRadius="lg"
                      bg={resultItem.is_correct ? 'green.50' : 'red.50'}
                      borderColor={resultItem.is_correct ? 'green.200' : 'red.200'} shadow="sm"
                  >
                    <Text fontWeight="bold" fontSize="lg" mb={2} color={resultItem.is_correct ? 'green.700' : 'red.700'}>
                      문제 {index + 1}. {resultItem.question || questions[index]?.question || "문제 정보 없음"} ({resultItem.is_correct ? "정답 👍" : "오답 👎"})
                    </Text>
                    <Text color={resultItem.is_correct ? 'green.600' : 'red.600'} mb={1}>
                      <Text as="span" fontWeight="medium">내 답변:</Text> {resultItem.user_answer || "답변 없음"}
                    </Text>
                    {!resultItem.is_correct && (
                        <Text color="blue.600" mb={1}>
                          <Text as="span" fontWeight="medium">정답:</Text> {resultItem.correct_answer}
                        </Text>
                    )}
                    {(resultItem.feedback || resultItem.explanation || questions[index]?.explanation) && (
                        <Text fontSize="sm" color="gray.700" mt={2} p={2} bg="gray.100" borderRadius="sm" borderLeft="3px" borderColor="gray.300">
                          <strong>피드백/해설:</strong> {resultItem.feedback || resultItem.explanation || questions[index]?.explanation}
                        </Text>
                    )}
                  </Box>
              ))}
            </VStack>

            <HStack direction={{base: "column", md: "row"} as const} spacing={4} justify="center" mt={6}>
              <Button colorScheme="blue" onClick={handleReset} size="lg" minW="150px">
                다시 풀기
              </Button>
              {showSaveButton && (
                  <Button colorScheme="green" onClick={handleSaveQuestions} isLoading={loading} size="lg" minW="150px">
                    문제 저장하기
                  </Button>
              )}
            </HStack>
          </VStack>
      );
    } else {
      // submitted는 true이지만, quizEvalResults가 null이거나, total 객체 또는 score_percentage가 유효하지 않은 경우
      return (
          <VStack p={5} spacing={3} textAlign="center" borderWidth="1px" borderRadius="lg" shadow="md" bg="white" mt={8}>
            <Heading size="lg" color="red.500">결과 표시 중 오류 발생</Heading>
            <Text>{apiError || "알 수 없는 오류로 결과를 표시할 수 없습니다."}</Text>
            <Text fontSize="sm" color="gray.500">개발자 콘솔(F12)에서 'Full API Response Data' 또는 'Backend Error Response Data' 로그를 확인하여 백엔드 응답을 점검해주세요.</Text>
            {quizEvalResults && ( // quizEvalResults가 null이 아닐 때만 (즉, 형식이 잘못된 데이터라도 있을 때) 표시
                <Box as="pre" mt={4} p={3} bg="gray.100" borderRadius="md" w="full" maxW="600px" overflowX="auto" whiteSpace="pre-wrap" textAlign="left">
                  {JSON.stringify(quizEvalResults, null, 2)}
                </Box>
            )}
            <Button colorScheme="gray" onClick={handleReset} mt={4}>퀴즈 초기화</Button>
          </VStack>
      );
    }
  }

  // ----- 2. 퀴즈 풀이 UI -----
  if (!currentQuestion) {
    // questions 배열이 비어 있거나, 아직 로드 중이거나, 로드에 실패했을 때
    // 초기 로딩은 부모 컴포넌트에서 처리하거나, 이 컴포넌트가 직접 로딩한다면 여기서 스피너 표시
    return (
        <VStack p={5} spacing={3} textAlign="center" mt={8}>
          {/* questions prop이 비어있다는 것은 부모 컴포넌트에서 문제를 아직 전달하지 않았거나 생성된 문제가 없다는 의미 */}
          <Heading size="md">퀴즈 준비 중...</Heading>
          <Text>표시할 문제가 없거나 문제를 불러오는 중입니다.</Text>
          {/* 부모 컴포넌트에서 로딩 상태를 관리하고 있다면, 그에 따라 스피너를 보여줄 수 있음 */}
        </VStack>
    );
  }

  return (
      <Box w="full" p={{base: 2, md: 4}} borderWidth="1px" borderRadius="lg" shadow="md" bg="white">
        <VStack spacing={6} align="stretch">
          {questions.length > 1 && (
              <>
                <Progress value={progress} size="sm" colorScheme="teal" borderRadius="md"/>
                <Text textAlign="right" fontSize="sm" color="gray.600">
                  문제 {currentIndex + 1} / {questions.length}
                </Text>
              </>
          )}

          <Box p={{base:2, md:4}} borderWidth={1} borderRadius="md" borderColor="gray.200">
            <Heading size="md" mb={4} lineHeight="tall">
              {currentQuestion.question}
            </Heading>

            {currentQuestion.type === 'multiple_choice' && currentQuestion.options ? (
                <RadioGroup
                    value={answers[currentIndex]}
                    onChange={handleAnswerChange}
                    colorScheme="teal"
                >
                  <Stack spacing={3}>
                    {currentQuestion.options.map((option, index) => (
                        <Radio
                            key={`${currentQuestion.id}-opt-${index}`}
                            value={option}
                            size="lg" p={1.5} borderWidth="1px" borderRadius="md"
                            borderColor="gray.300" _hover={{bg:"teal.50"}}
                        >
                          {option}
                        </Radio>
                    ))}
                  </Stack>
                </RadioGroup>
            ) : currentQuestion.type === 'short_answer' ? (
                <Textarea
                    value={answers[currentIndex]}
                    onChange={(e) => handleAnswerChange(e.target.value)}
                    placeholder="답을 입력하세요..."
                    size="lg"
                    minHeight="100px"
                    focusBorderColor="teal.500"
                />
            ) : (
                <Text color="gray.500">지원하지 않는 문제 유형입니다: {currentQuestion.type}</Text>
            )}
          </Box>

          <HStack direction={{base: "column", md: "row"} as const} spacing={4} justifyContent="space-between">
            <Button
                onClick={handlePrevious}
                isDisabled={currentIndex === 0}
                variant="outline"
                colorScheme="gray"
                size="lg"
                w={{base: "full", md: "auto"}}
            >
              이전
            </Button>

            {currentIndex === questions.length - 1 ? (
                <Button
                    onClick={handleSubmitAll}
                    colorScheme="green"
                    isLoading={loading}
                    loadingText="제출 중..."
                    size="lg"
                    w={{base: "full", md: "auto"}}
                >
                  모든 답안 제출하기
                </Button>
            ) : (
                <Button
                    onClick={handleNext}
                    colorScheme="teal"
                    size="lg"
                    w={{base: "full", md: "auto"}}
                >
                  다음
                </Button>
            )}
          </HStack>
        </VStack>
      </Box>
  );
}