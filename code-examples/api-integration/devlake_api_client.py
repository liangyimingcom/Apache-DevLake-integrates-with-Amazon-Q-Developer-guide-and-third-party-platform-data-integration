#!/usr/bin/env python3
"""
DevLake API客户端示例
方案2: DevLake API接口 - 标准化的数据集成方案
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

class DevLakeAPIClient:
    """DevLake API客户端类"""
    
    def __init__(self, base_url: str = "http://localhost:8080", timeout: int = 30):
        """
        初始化API客户端
        
        Args:
            base_url: DevLake API基础URL
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            **kwargs: 其他请求参数
            
        Returns:
            requests.Response: HTTP响应对象
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {e}")
            raise
    
    def get_version(self) -> Dict:
        """获取DevLake版本信息"""
        response = self._make_request('GET', '/version')
        return response.json()
    
    def get_q_dev_connections(self) -> List[Dict]:
        """获取Q Dev连接列表"""
        response = self._make_request('GET', '/plugins/q_dev/connections')
        return response.json()
    
    def create_q_dev_connection(self, connection_data: Dict) -> Dict:
        """
        创建Q Dev连接
        
        Args:
            connection_data: 连接配置数据
            
        Returns:
            Dict: 创建的连接信息
        """
        response = self._make_request(
            'POST', 
            '/plugins/q_dev/connections',
            json=connection_data,
            headers={'Content-Type': 'application/json'}
        )
        return response.json()
    
    def get_connection_detail(self, connection_id: int) -> Dict:
        """获取连接详细信息"""
        response = self._make_request('GET', f'/plugins/q_dev/connections/{connection_id}')
        return response.json()
    
    def test_connection(self, connection_id: int) -> Dict:
        """测试连接"""
        response = self._make_request('POST', f'/plugins/q_dev/connections/{connection_id}/test')
        return response.json()
    
    def get_pipelines(self) -> List[Dict]:
        """获取数据管道列表"""
        response = self._make_request('GET', '/pipelines')
        return response.json()
    
    def create_pipeline(self, pipeline_data: Dict) -> Dict:
        """
        创建数据管道
        
        Args:
            pipeline_data: 管道配置数据
            
        Returns:
            Dict: 创建的管道信息
        """
        response = self._make_request(
            'POST',
            '/pipelines',
            json=pipeline_data,
            headers={'Content-Type': 'application/json'}
        )
        return response.json()
    
    def get_pipeline_status(self, pipeline_id: int) -> Dict:
        """获取管道运行状态"""
        response = self._make_request('GET', f'/pipelines/{pipeline_id}')
        return response.json()
    
    def run_pipeline(self, pipeline_id: int) -> Dict:
        """运行数据管道"""
        response = self._make_request('POST', f'/pipelines/{pipeline_id}/run')
        return response.json()
    
    def get_store_onboard(self) -> Dict:
        """获取存储初始化状态"""
        response = self._make_request('GET', '/store/onboard')
        return response.json()

class QDevMetricsAPI:
    """Q Dev指标API封装类"""
    
    def __init__(self, devlake_client: DevLakeAPIClient):
        """
        初始化Q Dev指标API
        
        Args:
            devlake_client: DevLake API客户端实例
        """
        self.client = devlake_client
    
    def setup_q_dev_connection(self, config: Dict) -> Dict:
        """
        设置Q Dev连接
        
        Args:
            config: Q Dev连接配置
            
        Returns:
            Dict: 连接信息
        """
        connection_data = {
            "name": config.get("name", "q_dev_connection"),
            "accessKeyId": config["accessKeyId"],
            "secretAccessKey": config["secretAccessKey"],
            "region": config["region"],
            "bucket": config["bucket"],
            "identityStoreId": config.get("identityStoreId"),
            "identityStoreRegion": config.get("identityStoreRegion", config["region"]),
            "rateLimitPerHour": config.get("rateLimitPerHour", 20000)
        }
        
        return self.client.create_q_dev_connection(connection_data)
    
    def create_metrics_pipeline(self, connection_id: int, pipeline_name: str = "Q Dev Metrics Collection") -> Dict:
        """
        创建Q Dev指标收集管道
        
        Args:
            connection_id: 连接ID
            pipeline_name: 管道名称
            
        Returns:
            Dict: 管道信息
        """
        pipeline_data = {
            "name": pipeline_name,
            "plan": [
                [
                    {
                        "plugin": "q_dev",
                        "connectionId": connection_id,
                        "scope": [
                            {
                                "name": "Q Dev User Metrics"
                            }
                        ]
                    }
                ]
            ]
        }
        
        return self.client.create_pipeline(pipeline_data)
    
    def wait_for_pipeline_completion(self, pipeline_id: int, max_wait_time: int = 1800) -> Dict:
        """
        等待管道完成
        
        Args:
            pipeline_id: 管道ID
            max_wait_time: 最大等待时间（秒）
            
        Returns:
            Dict: 最终管道状态
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status = self.client.get_pipeline_status(pipeline_id)
            
            if status.get('status') in ['COMPLETED', 'FAILED']:
                return status
            
            print(f"管道运行中... 状态: {status.get('status', 'UNKNOWN')}")
            time.sleep(30)  # 等待30秒后再次检查
        
        raise TimeoutError(f"管道在{max_wait_time}秒内未完成")

def main():
    """示例使用方法"""
    print("=== DevLake API客户端示例 ===\n")
    
    # 初始化API客户端
    client = DevLakeAPIClient("http://<EC2-PUBLIC-IP>:8080")
    qdev_api = QDevMetricsAPI(client)
    
    try:
        # 1. 检查DevLake版本
        print("1. 检查DevLake版本:")
        version = client.get_version()
        print(f"   版本: {version}")
        print()
        
        # 2. 检查现有连接
        print("2. 检查现有Q Dev连接:")
        connections = client.get_q_dev_connections()
        print(f"   找到 {len(connections)} 个连接")
        
        if connections:
            for conn in connections:
                print(f"   - 连接ID: {conn['id']}, 名称: {conn['name']}")
        print()
        
        # 3. 如果没有连接，创建新连接
        if not connections:
            print("3. 创建Q Dev连接:")
            config = {
                "name": "q_dev_connection_api",
                "accessKeyId": "AKIAXXXXXXXXXXXXXXXX",
                "secretAccessKey": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "region": "us-east-1",
                "bucket": "<YOUR-S3-BUCKET-NAME>",
                "identityStoreId": "<YOUR-IDENTITY-STORE-ID>",
                "identityStoreRegion": "us-east-1"
            }
            
            new_connection = qdev_api.setup_q_dev_connection(config)
            print(f"   连接已创建: ID={new_connection['id']}")
            connection_id = new_connection['id']
        else:
            connection_id = connections[0]['id']
        
        # 4. 测试连接
        print(f"4. 测试连接 (ID: {connection_id}):")
        try:
            test_result = client.test_connection(connection_id)
            print(f"   连接测试结果: {test_result}")
        except Exception as e:
            print(f"   连接测试失败: {e}")
        print()
        
        # 5. 检查管道
        print("5. 检查数据管道:")
        pipelines = client.get_pipelines()
        print(f"   找到 {len(pipelines)} 个管道")
        
        if pipelines:
            for pipeline in pipelines:
                print(f"   - 管道ID: {pipeline['id']}, 名称: {pipeline['name']}")
        print()
        
        # 6. 创建数据收集管道（如果需要）
        if not pipelines:
            print("6. 创建数据收集管道:")
            pipeline = qdev_api.create_metrics_pipeline(connection_id)
            print(f"   管道已创建: ID={pipeline['id']}")
            
            # 运行管道
            print("7. 运行数据收集管道:")
            run_result = client.run_pipeline(pipeline['id'])
            print(f"   管道启动结果: {run_result}")
        
        # 7. 检查存储状态
        print("8. 检查存储状态:")
        store_status = client.get_store_onboard()
        print(f"   存储状态: {store_status}")
        
        print("\n=== API客户端示例完成 ===")
        
    except Exception as e:
        print(f"执行错误: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
