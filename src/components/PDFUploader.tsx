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
      const response = await axios.post('https://edubackend-production.up.railway.app/api/upload-pdf', formData, {
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
        <Heading size="lg" textAlign="center">
          PDF를 업로드하고 학습자료를 선택해주세요!
        </Heading>

        <Box
          p={10}
          bg="white"
          borderWidth={4}
          borderRadius="lg"
          borderStyle="dashed"
          borderColor="blue.200"
          textAlign="center"
          shadow="md"
        >
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
            id="pdf-upload"
          />

          <label htmlFor="pdf-upload">
            <Button
              as="span"
              colorScheme="blue"
              isLoading={isUploading}
              leftIcon={<Upload size={18} />}
            >
              PDF 업로드
            </Button>
          </label>

          <Text mt={4} color="gray.500">
            업로드된 문서는 서버에 저장되며, 추후 선택하여 문제를 생성할 수 있습니다.
          </Text>
        </Box>
      </VStack>
  );
}