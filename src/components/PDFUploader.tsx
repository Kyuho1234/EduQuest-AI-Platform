'use client';

import { Box, Button, Text, useToast, VStack, Heading } from '@chakra-ui/react';
import { useState } from 'react';
import axios from 'axios';
import { useSession } from 'next-auth/react';
import { Upload } from 'lucide-react'

interface PDFUploaderProps {
  onUploadComplete: (documentId: string) => void;
}

export default function PDFUploader({ onUploadComplete }: PDFUploaderProps) {
  const [isUploading, setIsUploading] = useState(false);
  const toast = useToast();
  const { data: session } = useSession();

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.pdf')) {
      toast({
        title: '오류',
        description: 'PDF 파일만 업로드 가능합니다.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (!session?.user?.id) {
      toast({
        title: '로그인 필요',
        description: 'PDF를 업로드하려면 로그인해야 합니다.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', session.user.id);

    setIsUploading(true);

    try {
      const response = await axios.post('http://localhost:8000/api/upload-pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const documentId = response.data.document_id;
      onUploadComplete(documentId);

      toast({
        title: '업로드 성공',
        description: '문서가 저장되었습니다. 목록에서 선택해 문제를 생성하세요.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: '업로드 실패',
        description: '파일 업로드 중 오류가 발생했습니다.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <VStack spacing={6}>
        {/* 제목 텍스트 */}
        <Heading size="lg" textAlign="center">
          PDF를 업로드하고 학습자료를 선택해주세요!
        </Heading>

        {/* 업로드 UI 박스 */}
        <Box
          p={10}                    // 내부 여백
          bg="white"               // 배경 흰색
          borderWidth={4}          // 테두리 두께
          borderRadius="lg"        // 모서리 둥글게
          borderStyle="dashed"     // 점선 테두리
          borderColor="blue.200"   // 테두리 색상
          textAlign="center"       // 텍스트 중앙 정렬
          shadow="md"              // 그림자 효과
        >
          {/* 실제 파일 input은 숨기고, label로 감싼다 */}
          <input
            type="file"
            accept=".pdf"                  // PDF만 허용
            onChange={handleFileUpload}   // 파일 선택 시 이벤트 발생
            style={{ display: 'none' }}   // 시각적으로 숨김
            id="pdf-upload"               // label과 연결할 ID
          />

          {/* 라벨을 통해 숨긴 input을 클릭 가능하게 함 */}
          <label htmlFor="pdf-upload">
            <Button
              as="span"                // label 내부에서 버튼처럼 보이게 하기 위함
              colorScheme="blue"      // 파란색 버튼 스타일
              isLoading={isUploading} // 업로드 중 로딩 스피너 표시
              leftIcon={<Upload size={18} />} // 왼쪽에 Upload 아이콘 추가
            >
              PDF 업로드
            </Button>
          </label>

          {/* 안내 텍스트 */}
          <Text mt={4} color="gray.500">
            업로드된 문서는 서버에 저장되며, 추후 선택하여 문제를 생성할 수 있습니다.
          </Text>
        </Box>
      </VStack>
  );
}
