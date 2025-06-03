'use client';

import { useEffect } from 'react';
import { useSession, signOut } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import {
  Button,
  VStack,
  Heading,
  Center,
  Spinner,
  Text,
  Box,
  Image,
  HStack,
  Flex,
  Divider
} from '@chakra-ui/react';

export default function Home() {
  const router = useRouter();
  const { data: session, status } = useSession();

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

  const handleNavigate = (path: string) => {
    router.push(path);
  };

  return (
      <>
        {/* 상단 바 */}
        <Flex
            as="header"
            justify="space-between"
            align="center"
            w="full"
            px={6}
            py={4}
            position="absolute"
            top={0}
            left={0}
            zIndex={10}
            bg="white"

        >
          <Box fontSize="xl" fontWeight="bold">
            EduQuest AI
          </Box>
          <Button colorScheme="red" size="md" onClick={() => signOut()}>
            로그아웃
          </Button>
        </Flex>

        <Box h="72px" />
        <Divider borderColor="gray.400" />

        {/* 메인 콘텐츠 */}
        <Center py={10} pt={20}>
          <VStack spacing={10} w="full" maxW="5xl" px={6} align="stretch">
            <Box textAlign="center">
              <Heading size="2xl">EduQuest AI</Heading>
              <Text fontSize="4xl" mt={2}>퀴즈 생성기</Text>
            </Box>

            <Center>
              <VStack spacing={6}>
                <Button colorScheme="teal" size="lg" onClick={() => handleNavigate('/questions-generate')}>
                  문제 생성
                </Button>
                <Button colorScheme="teal" size="lg" onClick={() => handleNavigate('/my-questions')}>
                  문제 조회
                </Button>
                <Button colorScheme="teal" size="lg" onClick={() => handleNavigate('/document-management')}>
                  학습자료 관리
                </Button>
              </VStack>
            </Center>

            <Box h={0} />

            {/* 설명 섹션 1 */}
            <Center>
              <Box textAlign="center">
                <Text fontSize="3xl" fontWeight="bold" mb={2}>
                  EduQuest AI 퀴즈 생성기를 사용해 보세요.
                </Text>
                <Text>
                  EduQuest AI 문제 생성기로 모든 PDF 문서에서 시험과 학습을 위한 문제 및 정답을 빠르게 만들어보세요.
                </Text>
              </Box>
            </Center>

            <Box h={8} />

            {/* 설명 섹션 2 */}
            <HStack spacing={10} align="start" flexWrap="wrap" >
              <Image src="/photo1.png" alt="기능 설명 이미지 2" boxSize="300px" objectFit="cover" />
              <Box flex="2">
                <Text fontSize="xl" fontWeight="bold" mb={2}>
                  퀴즈 즉시 생성
                </Text>
                <Text whiteSpace="pre-line">
                  PDF 파일만 업로드하면, AI 문제 생성기가 나머지를 알아서 처리해 드립니다.{"\n"}
                  몇 번의 클릭만으로 원하는 시험이나 퀴즈를 손쉽게 만들 수 있습니다.{"\n"}
                  더 빠르고, 더 똑똑한 문제 출제 도구를 지금 만나보세요.
                </Text>
              </Box>
            </HStack>

            <Box h={4} />

            {/* 설명 섹션 3 */}
            <HStack spacing={10} align="start" flexWrap="wrap">
              <Box flex="1">
                <Text fontSize="xl" fontWeight="bold" mb={2}>
                  다양한 문제 유형
                </Text>
                <Text whiteSpace="pre-line">
                  다양한 주제를 아우르는 객관식 및 서술형 문제를 손쉽게 생성할 수 있습니다.{"\n"}
                  이 시험 생성기를 활용하여 학생 평가 또는 개인 학습용 퀴즈 등 {"\n"}
                  여러 목적에 맞는 문제를 만들고, 이에 대한 상세한 피드백도 받아보세요.
                </Text>
              </Box>
              <Image src="/photo2.png" alt="기능 설명 이미지 3" boxSize="300px" objectFit="cover" />
            </HStack>

            <Box h={4} />

            {/* 사용 방법 안내 */}
            <HStack spacing={10} align="start" flexWrap="wrap">
              <Image src="/photo3.png" alt="기능 설명 이미지 4" boxSize="300px" objectFit="cover" />
              <Box flex="1">
                <Heading size="md" mb={4}>온라인에서 AI 문제를 생성하는 방법</Heading>
                <VStack align="start" spacing={2} fontSize="md">
                  <Text whiteSpace="pre-line">1. 로그인 한 후 PDF 파일을 업로드 하세요.{"\n"}
                  2. 만들고 싶은 문제 유형을 선택하고 '문제 생성' 버튼을 클릭하세요.{"\n"}
                  3. '문제 저장'를 클릭하여 문제와 정답을 저장하세요.{"\n"}
                  4. '문제 조회'를 클릭하여 푼 문제의 피드백 및 정답을 확인하세요.{"\n"}
                  </Text>
                </VStack>
              </Box>
            </HStack>
          </VStack>
        </Center>
      </>
  );
}
