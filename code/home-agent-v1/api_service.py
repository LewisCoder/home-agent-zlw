#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 服务层
封装所有外部 API 调用
"""

import requests
from typing import Dict, Any
from config import config


class APIService:
    """API 服务基类"""

    def __init__(self):
        self.headers = config.default_headers
        self.timeout = config.api_timeout

    def _handle_request(self, url: str, payload: dict) -> Dict[str, Any]:
        """
        统一的 API 请求处理

        Args:
            url: API 地址
            payload: 请求体

        Returns:
            统一格式的响应
        """
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()

            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json()
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "请求超时,请稍后重试",
                "error_type": "timeout"
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "连接失败,请检查网络或 API 地址",
                "error_type": "connection_error"
            }
        except requests.exceptions.HTTPError as e:
            return {
                "success": False,
                "error": f"HTTP 错误: {e}",
                "status_code": getattr(e.response, 'status_code', None),
                "error_type": "http_error"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"未知错误: {str(e)}",
                "error_type": "unknown"
            }


class BillService(APIService):
    """账单服务"""

    def query_bill(self, bill_code: str) -> Dict[str, Any]:
        """
        查询账单信息

        Args:
            bill_code: 账单代码

        Returns:
            API 响应结果
        """
        payload = {"billCode": bill_code}
        return self._handle_request(config.bill_api_url, payload)


class OperateLogService(APIService):
    """操作记录服务"""

    def query_operate_log(
        self,
        business_key: str,
        current_page: int = 1,
        page_size: int = None
    ) -> Dict[str, Any]:
        """
        查询操作记录

        Args:
            business_key: 业务键(账单代码)
            current_page: 当前页码
            page_size: 每页大小

        Returns:
            API 响应结果
        """
        if page_size is None:
            page_size = config.default_page_size

        payload = {
            "currentPage": current_page,
            "pageSize": page_size,
            "businessKey": business_key,
            "businessModuleName": "内控工作台"
        }

        return self._handle_request(config.operate_log_api_url, payload)


# 服务实例
bill_service = BillService()
operate_log_service = OperateLogService()
