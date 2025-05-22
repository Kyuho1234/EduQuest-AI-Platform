'use client';

import { useState, useRef } from 'react';
import { 
  Box, Container, Heading, Text, Button, Input, FormControl, 
  FormLabel, VStack, HStack, Spinner, Alert, AlertIcon, 
  AlertTitle, AlertDescription, Tabs, TabList, Tab, TabPanels, 
  TabPanel, Card, CardBody, Divider, Stack, useToast,
  List, ListItem, UnorderedList, OrderedList, Badge, Textarea
} from '@chakra-ui/react';
import axios from 'axios';

// 임시 사용자 ID
const TEMP_USER_ID = "user123";

export default function QuestionsGeneratePage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();
  
  const [activeTab, setActiveTab] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedDocId, setUploadedDocId] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState(false);
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedQuestions, setGeneratedQuestions] = useState<any[]>([]);
  
  const [directText, setDirectText] = useState("");
  const [isGeneratingFromText, setIsGeneratingFromText] = useState(false);
  
  // 파일 선택 처리
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      
      // PDF 파일만 허용
      if (selectedFile.type !== 'application/pdf') {
        toast({
          title: "파일 형식 오류",
          description: "PDF 파일만 업로드할 수 있습니다.",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
        return;
      }
      
      setFile(selectedFile);
      setUploadSuccess(false);
      setUploadedDocId("");
    }
  };
  
  // 파일 업로드 처리
  const handleUpload = async () => {
    if (!file) {
      toast({
        title: "파일 없음",
        description: "업로드할 PDF 파일을 선택해주세요.",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('user_id', TEMP_USER_ID);
      
      const response = await axios.post('/api/upload-pdf', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      if (response.data.success) {
        setUploadSuccess(true);
        setUploadedDocId(response.data.document_id);
        toast({
          title: "업로드 성공",
          description: `${file.name} 파일이 성공적으로 업로드되었습니다.`,
          status: "success",
          duration: 3000,
          isClosable: true,
        });
      } else {
        throw new Error("업로드 실패");
      }
    } catch (error) {
      console.error("파일 업로드 오류:", error);
      toast({
        title: "업로드 실패",
        description: "파일 업로드 중 오류가 발생했습니다.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsUploading(false);
    }
  };
  
  // 문제 생성 처리 (PDF)
  const handleGenerateQuestions = async () => {
    if (!uploadedDocId) {
      toast({
        title: "문서 ID 없음",
        description: "먼저 PDF 파일을 업로드해주세요.",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    setIsGenerating(true);
    
    try {
      const response = await axios.post('/api/generate-questions-from-document', {
        document_id: uploadedDocId,
        user_id: TEMP_USER_ID
      });
      
      if (response.data.success) {
        setGeneratedQuestions(response.data.questions);
        toast({
          title: "문제 생성 완료",
          description: `${response.data.questions.length}개의 문제가 생성되었습니다.`,
          status: "success",
          duration: 3000,
          isClosable: true,
        });
      } else {
        throw new Error(response.data.message || "문제 생성 실패");
      }
    } catch (error: any) {
      console.error("문제 생성 오류:", error);
      toast({
        title: "문제 생성 실패",
        description: error.message || "문제 생성 중 오류가 발생했습니다.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsGenerating(false);
    }
  };
  
  // 직접 입력한 텍스트로 문제 생성
  const handleGenerateFromText = async () => {
    if (!directText.trim()) {
      toast({
        title: "텍스트 없음",
        description: "문제를 생성할 텍스트를 입력해주세요.",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    setIsGeneratingFromText(true);
    
    try {
      const response = await axios.post('/api/generate-questions', {
        text: directText,
        user_id: TEMP_USER_ID
      });
      
      if (response.data.success) {
        setGeneratedQuestions(response.data.questions);
        toast({
          title: "문제 생성 완료",
          description: `${response.data.questions.length}개의 문제가 생성되었습니다.`,
          status: "success",
          duration: 3000,
          isClosable: true,
        });
      } else {
        throw new Error(response.data.message || "문제 생성 실패");
      }
    } catch (error: any) {
      console.error("문제 생성 오류:", error);
      toast({
        title: "문제 생성 실패",
        description: error.message || "문제 생성 중 오류가 발생했습니다.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsGeneratingFromText(false);
    }
  };
  
  // 문제 저장
  const handleSaveQuestions = async () => {
    if (!generatedQuestions.length) {
      toast({
        title: "저장할 문제 없음",
        description: "먼저 문제를 생성해주세요.",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    try {
      // 문제 형식 변환
      const questionsToSave = generatedQuestions.map(q => ({
        question: q.question,
        correct_answer: q.correct_answer,
        explanation: q.explanation,
        options: q.options || [],
        type: q.type || "multiple_choice"
      }));
      
      const response = await axios.post('/api/save-questions', {
        user_id: TEMP_USER_ID,
        questions: questionsToSave
      });
      
      if (response.data.success) {
        toast({
          title: "저장 성공",
          description: response.data.message,
          status: "success",
          duration: 3000,
          isClosable: true,
        });
      } else {
        throw new Error(response.data.message || "저장 실패");
      }
    } catch (error: any) {
      console.error("문제 저장 오류:", error);
      toast({
        title: "저장 실패",
        description: error.message || "문제 저장 중 오류가 발생했습니다.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  return (
    <Box py={8}>
      <Container maxW="container.lg">
        <VStack spacing={8} align="stretch">
          <Box textAlign="center">
            <Heading as="h1" size="xl" mb={2}>문제 생성</Heading>
            <Text color="gray.600">PDF 문서 업로드 또는 텍스트 직접 입력으로 AI 문제를 생성하세요</Text>
          </Box>
          
          <Tabs isFitted variant="enclosed" index={activeTab} onChange={setActiveTab}>
            <TabList mb="1em">
              <Tab>PDF 업로드</Tab>
              <Tab>텍스트 직접 입력</Tab>
            </TabList>
            
            <TabPanels>
              {/* PDF 업로드 탭 */}
              <TabPanel>
                <VStack spacing={5} align="stretch">
                  <FormControl>
                    <FormLabel>PDF 파일 선택</FormLabel>
                    <Input
                      type="file"
                      ref={fileInputRef}
                      accept=".pdf"
                      onChange={handleFileChange}
                      display="none"
                    />
                    <HStack>
                      <Button 
                        onClick={() => fileInputRef.current?.click()}
                        colorScheme="blue"
                      >
                        파일 선택
                      </Button>
                      <Text>
                        {file ? file.name : "선택된 파일 없음"}
                      </Text>
                    </HStack>
                  </FormControl>
                  
                  <Button 
                    colorScheme="teal" 
                    onClick={handleUpload}
                    isLoading={isUploading}
                    loadingText="업로드 중..."
                    isDisabled={!file}
                  >
                    업로드
                  </Button>
                  
                  {uploadSuccess && (
                    <Alert status="success">
                      <AlertIcon />
                      <AlertTitle>업로드 성공!</AlertTitle>
                      <AlertDescription>
                        이제 문제 생성 버튼을 클릭하여 AI 문제를 생성하세요.
                      </AlertDescription>
                    </Alert>
                  )}
                  
                  <Button 
                    colorScheme="green" 
                    onClick={handleGenerateQuestions}
                    isLoading={isGenerating}
                    loadingText="문제 생성 중..."
                    isDisabled={!uploadSuccess}
                    size="lg"
                    mt={4}
                  >
                    PDF에서 문제 생성하기
                  </Button>
                </VStack>
              </TabPanel>
              
              {/* 텍스트 직접 입력 탭 */}
              <TabPanel>
                <VStack spacing={5} align="stretch">
                  <FormControl>
                    <FormLabel>문제를 생성할 텍스트</FormLabel>
                    <Textarea
                      value={directText}
                      onChange={(e) => setDirectText(e.target.value)}
                      placeholder="여기에 교재 내용이나 문제로 만들 텍스트를 입력하세요..."
                      size="md"
                      rows={10}
                    />
                  </FormControl>
                  
                  <Button 
                    colorScheme="green" 
                    onClick={handleGenerateFromText}
                    isLoading={isGeneratingFromText}
                    loadingText="문제 생성 중..."
                    isDisabled={!directText.trim()}
                    size="lg"
                  >
                    텍스트로 문제 생성하기
                  </Button>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
          
          {/* 생성된 문제 표시 영역 */}
          {generatedQuestions.length > 0 && (
            <Box mt={8}>
              <Heading as="h2" size="lg" mb={4}>생성된 문제</Heading>
              
              <VStack spacing={6} align="stretch">
                {generatedQuestions.map((question, index) => (
                  <Card key={index}>
                    <CardBody>
                      <VStack align="stretch" spacing={4}>
                        <HStack>
                          <Heading size="md">문제 {index + 1}</Heading>
                          {question.reliability_score && (
                            <Badge colorScheme={question.reliability_score > 0.7 ? "green" : 
                                              question.reliability_score > 0.5 ? "yellow" : "red"}>
                              신뢰도: {(question.reliability_score * 100).toFixed(0)}%
                            </Badge>
                          )}
                        </HStack>
                        
                        <Text fontWeight="bold">{question.question}</Text>
                        
                        <Box>
                          <Text fontWeight="medium" mb={2}>보기:</Text>
                          <OrderedList spacing={1} pl={5}>
                            {question.options?.map((option: string, idx: number) => (
                              <ListItem key={idx}>
                                {option}
                              </ListItem>
                            ))}
                          </OrderedList>
                        </Box>
                        
                        <Divider />
                        
                        <Box>
                          <Text fontWeight="medium">정답:</Text>
                          <Text>{question.correct_answer}</Text>
                        </Box>
                        
                        <Box>
                          <Text fontWeight="medium">해설:</Text>
                          <Text>{question.explanation}</Text>
                        </Box>
                      </VStack>
                    </CardBody>
                  </Card>
                ))}
              </VStack>
              
              <Button 
                colorScheme="purple" 
                onClick={handleSaveQuestions}
                mt={6}
                size="lg"
                width="full"
              >
                생성된 문제 저장하기
              </Button>
            </Box>
          )}
        </VStack>
      </Container>
    </Box>
  );
}