from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """A2A Protocol 메시지 처리"""
        try:
            if "function_call" in message:
                function_name = message["function_call"]["name"]
                arguments = message["function_call"]["arguments"]
                result = await self.execute_function(function_name, arguments)
                return {
                    "role": self.name,
                    "content": result,
                    "status": "success"
                }
        except Exception as e:
            return {
                "role": self.name,
                "content": str(e),
                "status": "error"
            }
    
    @abstractmethod
    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """함수 실행 - 하위 클래스에서 구현"""
        pass 