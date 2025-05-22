import Link from 'next/link';
import { ChakraProvider, Box, Heading, Text, Button, VStack, Container, Flex, SimpleGrid } from '@chakra-ui/react';

export default function Home() {
  return (
    <ChakraProvider>
      <Box bg="gray.50" minH="100vh">
        {/* Hero Section */}
        <Box bg="blue.600" color="white" py={16}>
          <Container maxW="container.xl">
            <VStack spacing={6} align="center" textAlign="center">
              <Heading as="h1" size="2xl">EduQuest AI 학습 플랫폼</Heading>
              <Text fontSize="xl" maxW="3xl">
                인공지능을 활용한 교육용 문제 생성 및 학습 지원 시스템입니다.
                PDF 문서를 업로드하면 AI가 자동으로 문제를 생성하고, RAG 기술로
                정확한 학습 지원을 제공합니다.
              </Text>
              <Flex gap={4} mt={4}>
                <Button as={Link} href="/questions-generate" size="lg" colorScheme="green">
                  문제 생성하기
                </Button>
                <Button as={Link} href="/my-questions" size="lg" colorScheme="teal" variant="outline">
                  내 문제 보기
                </Button>
              </Flex>
            </VStack>
          </Container>
        </Box>

        {/* Features Section */}
        <Box py={16}>
          <Container maxW="container.xl">
            <VStack spacing={12}>
              <Heading as="h2" size="xl">주요 기능</Heading>
              
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={10} width="100%">
                <FeatureCard 
                  title="문서 기반 문제 생성"
                  description="PDF 문서를 업로드하면 인공지능이 자동으로 핵심 개념에 대한 문제를 생성합니다."
                />
                <FeatureCard 
                  title="RAG 기반 검증"
                  description="생성된 문제가 입력 자료와 일치하는지 RAG 기술로 정확하게 검증합니다."
                />
                <FeatureCard 
                  title="맞춤형 피드백"
                  description="학습자의 답변을 채점하고 개인화된 피드백을 제공합니다."
                />
              </SimpleGrid>
            </VStack>
          </Container>
        </Box>

        {/* How It Works Section */}
        <Box py={16} bg="gray.100">
          <Container maxW="container.xl">
            <VStack spacing={10}>
              <Heading as="h2" size="xl">이용 방법</Heading>
              
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={10} width="100%">
                <StepCard 
                  number={1}
                  title="PDF 업로드"
                  description="학습하고자 하는 PDF 문서를 시스템에 업로드합니다."
                />
                <StepCard 
                  number={2}
                  title="문제 생성"
                  description="AI가 문서 내용을 분석하여 최적의 문제를 자동으로 생성합니다."
                />
                <StepCard 
                  number={3}
                  title="퀴즈 풀기"
                  description="생성된 문제로 퀴즈를 풀고 즉각적인 피드백을 받습니다."
                />
              </SimpleGrid>
              
              <Button as={Link} href="/questions-generate" size="lg" colorScheme="blue" mt={6}>
                지금 시작하기
              </Button>
            </VStack>
          </Container>
        </Box>
      </Box>
    </ChakraProvider>
  );
}

function FeatureCard({ title, description }: { title: string; description: string }) {
  return (
    <Box bg="white" p={8} borderRadius="lg" boxShadow="md" height="100%">
      <VStack align="start" spacing={4}>
        <Heading as="h3" size="md">{title}</Heading>
        <Text color="gray.600">{description}</Text>
      </VStack>
    </Box>
  );
}

function StepCard({ number, title, description }: { number: number; title: string; description: string }) {
  return (
    <Box bg="white" p={8} borderRadius="lg" boxShadow="md" height="100%">
      <VStack align="start" spacing={4}>
        <Flex 
          bg="blue.500" 
          color="white" 
          w={10} 
          h={10} 
          borderRadius="full" 
          justify="center" 
          align="center"
          fontWeight="bold"
        >
          {number}
        </Flex>
        <Heading as="h3" size="md">{title}</Heading>
        <Text color="gray.600">{description}</Text>
      </VStack>
    </Box>
  );
}