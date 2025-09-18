#!/usr/bin/env python3
"""
Q Dev指标数据JSON导出器
支持多种导出格式和自定义查询
"""

import mysql.connector
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os

class QDevJSONExporter:
    """Q Dev指标JSON导出器"""
    
    def __init__(self, host: str = 'localhost', port: int = 3306, 
                 user: str = 'merico', password: str = 'merico', database: str = 'lake'):
        """初始化导出器"""
        self.config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database
        }
    
    def get_connection(self):
        """获取数据库连接"""
        return mysql.connector.connect(**self.config)
    
    def export_user_metrics_summary(self, connection_id: int = 1) -> List[Dict]:
        """导出用户指标汇总数据"""
        query = """
        SELECT 
            user_id,
            display_name,
            first_date,
            last_date,
            total_days,
            total_inline_suggestions_count,
            total_inline_acceptance_count,
            acceptance_rate,
            total_inline_ai_code_lines,
            avg_inline_suggestions_count,
            avg_inline_acceptance_count,
            total_code_review_findings_count,
            created_at,
            updated_at
        FROM _tool_q_dev_user_metrics
        WHERE connection_id = %s
        ORDER BY total_inline_suggestions_count DESC
        """
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, [connection_id])
            results = cursor.fetchall()
            
            # 转换datetime对象为字符串
            for result in results:
                for key, value in result.items():
                    if isinstance(value, datetime):
                        result[key] = value.isoformat()
            
            return results
        finally:
            conn.close()
    
    def export_user_daily_data(self, connection_id: int = 1, 
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> List[Dict]:
        """导出用户日常数据"""
        query = """
        SELECT 
            user_id,
            display_name,
            date,
            inline_suggestions_count,
            inline_acceptance_count,
            inline_ai_code_lines,
            chat_messages_sent,
            chat_messages_interacted,
            code_fix_generation_event_count,
            test_generation_event_count,
            doc_generation_event_count,
            transformation_event_count,
            created_at
        FROM _tool_q_dev_user_data
        WHERE connection_id = %s
        """
        
        params = [connection_id]
        
        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= %s"
            params.append(end_date)
            
        query += " ORDER BY date DESC, user_id"
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # 转换datetime对象为字符串
            for result in results:
                for key, value in result.items():
                    if isinstance(value, datetime):
                        result[key] = value.isoformat()
            
            return results
        finally:
            conn.close()
    
    def export_aggregated_metrics(self, connection_id: int = 1) -> Dict:
        """导出聚合指标"""
        query = """
        SELECT 
            COUNT(*) as total_users,
            SUM(total_inline_suggestions_count) as total_suggestions,
            SUM(total_inline_acceptance_count) as total_acceptances,
            AVG(acceptance_rate) as avg_acceptance_rate,
            SUM(total_inline_ai_code_lines) as total_ai_code_lines,
            MIN(first_date) as earliest_date,
            MAX(last_date) as latest_date,
            AVG(total_days) as avg_active_days
        FROM _tool_q_dev_user_metrics
        WHERE connection_id = %s
        """
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, [connection_id])
            result = cursor.fetchone()
            
            # 转换datetime对象为字符串
            for key, value in result.items():
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, float):
                    result[key] = round(value, 2)
            
            return result
        finally:
            conn.close()
    
    def export_daily_trends(self, connection_id: int = 1, days: int = 30) -> List[Dict]:
        """导出日常趋势数据"""
        query = """
        SELECT 
            date,
            COUNT(DISTINCT user_id) as active_users,
            SUM(inline_suggestions_count) as daily_suggestions,
            SUM(inline_acceptance_count) as daily_acceptances,
            SUM(inline_ai_code_lines) as daily_ai_lines,
            SUM(chat_messages_sent) as daily_chat_messages,
            AVG(CASE WHEN inline_suggestions_count > 0 
                THEN inline_acceptance_count / inline_suggestions_count 
                ELSE 0 END) as daily_acceptance_rate
        FROM _tool_q_dev_user_data
        WHERE connection_id = %s 
          AND date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        GROUP BY date
        ORDER BY date DESC
        """
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, [connection_id, days])
            results = cursor.fetchall()
            
            # 转换数据类型
            for result in results:
                for key, value in result.items():
                    if isinstance(value, datetime):
                        result[key] = value.isoformat()
                    elif isinstance(value, float):
                        result[key] = round(value, 4)
            
            return results
        finally:
            conn.close()
    
    def export_user_rankings(self, connection_id: int = 1, limit: int = 10) -> Dict:
        """导出用户排行榜"""
        rankings = {}
        
        # 建议数排行
        query_suggestions = """
        SELECT user_id, display_name, total_inline_suggestions_count
        FROM _tool_q_dev_user_metrics
        WHERE connection_id = %s
        ORDER BY total_inline_suggestions_count DESC
        LIMIT %s
        """
        
        # 接受率排行
        query_acceptance = """
        SELECT user_id, display_name, acceptance_rate, total_inline_acceptance_count
        FROM _tool_q_dev_user_metrics
        WHERE connection_id = %s AND total_inline_suggestions_count > 0
        ORDER BY acceptance_rate DESC, total_inline_acceptance_count DESC
        LIMIT %s
        """
        
        # AI代码行数排行
        query_ai_lines = """
        SELECT user_id, display_name, total_inline_ai_code_lines
        FROM _tool_q_dev_user_metrics
        WHERE connection_id = %s
        ORDER BY total_inline_ai_code_lines DESC
        LIMIT %s
        """
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            
            # 建议数排行
            cursor.execute(query_suggestions, [connection_id, limit])
            rankings['top_suggestions'] = cursor.fetchall()
            
            # 接受率排行
            cursor.execute(query_acceptance, [connection_id, limit])
            rankings['top_acceptance_rate'] = cursor.fetchall()
            
            # AI代码行数排行
            cursor.execute(query_ai_lines, [connection_id, limit])
            rankings['top_ai_code_lines'] = cursor.fetchall()
            
            return rankings
        finally:
            conn.close()
    
    def export_complete_dataset(self, connection_id: int = 1, 
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> Dict:
        """导出完整数据集"""
        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'connection_id': connection_id,
                'start_date': start_date,
                'end_date': end_date,
                'exporter_version': '1.0.0'
            }
        }
        
        print("导出用户指标汇总...")
        export_data['user_metrics_summary'] = self.export_user_metrics_summary(connection_id)
        
        print("导出用户日常数据...")
        export_data['user_daily_data'] = self.export_user_daily_data(connection_id, start_date, end_date)
        
        print("导出聚合指标...")
        export_data['aggregated_metrics'] = self.export_aggregated_metrics(connection_id)
        
        print("导出日常趋势...")
        export_data['daily_trends'] = self.export_daily_trends(connection_id)
        
        print("导出用户排行榜...")
        export_data['user_rankings'] = self.export_user_rankings(connection_id)
        
        # 添加统计信息
        export_data['statistics'] = {
            'total_users': len(export_data['user_metrics_summary']),
            'total_daily_records': len(export_data['user_daily_data']),
            'date_range_days': len(export_data['daily_trends'])
        }
        
        return export_data
    
    def save_to_file(self, data: Dict, filename: str, pretty: bool = True) -> str:
        """保存数据到JSON文件"""
        # 确保目录存在
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            else:
                json.dump(data, f, ensure_ascii=False, default=str)
        
        return filename
    
    def export_to_multiple_files(self, connection_id: int = 1, 
                                output_dir: str = 'qdev_exports') -> Dict[str, str]:
        """导出到多个文件"""
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        files = {}
        
        # 导出用户指标汇总
        print("导出用户指标汇总...")
        user_metrics = self.export_user_metrics_summary(connection_id)
        files['user_metrics'] = self.save_to_file(
            user_metrics, 
            f"{output_dir}/user_metrics_{timestamp}.json"
        )
        
        # 导出用户日常数据
        print("导出用户日常数据...")
        daily_data = self.export_user_daily_data(connection_id)
        files['daily_data'] = self.save_to_file(
            daily_data,
            f"{output_dir}/daily_data_{timestamp}.json"
        )
        
        # 导出聚合指标
        print("导出聚合指标...")
        aggregated = self.export_aggregated_metrics(connection_id)
        files['aggregated'] = self.save_to_file(
            aggregated,
            f"{output_dir}/aggregated_metrics_{timestamp}.json"
        )
        
        # 导出完整数据集
        print("导出完整数据集...")
        complete_data = self.export_complete_dataset(connection_id)
        files['complete'] = self.save_to_file(
            complete_data,
            f"{output_dir}/complete_dataset_{timestamp}.json"
        )
        
        return files

def main():
    """示例使用方法"""
    print("=== Q Dev指标JSON导出器 ===\n")
    
    # 初始化导出器
    exporter = QDevJSONExporter(host='<EC2-PUBLIC-IP>')
    
    try:
        # 1. 导出完整数据集到单个文件
        print("1. 导出完整数据集:")
        complete_data = exporter.export_complete_dataset()
        
        filename = f"qdev_complete_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        exporter.save_to_file(complete_data, filename)
        print(f"   完整数据集已导出到: {filename}")
        
        # 显示统计信息
        stats = complete_data['statistics']
        print(f"   - 用户数: {stats['total_users']}")
        print(f"   - 日常记录数: {stats['total_daily_records']}")
        print(f"   - 日期范围: {stats['date_range_days']} 天")
        print()
        
        # 2. 导出到多个文件
        print("2. 导出到多个文件:")
        files = exporter.export_to_multiple_files()
        
        print("   导出的文件:")
        for file_type, filepath in files.items():
            file_size = os.path.getsize(filepath)
            print(f"   - {file_type}: {filepath} ({file_size} bytes)")
        print()
        
        # 3. 导出特定时间范围的数据
        print("3. 导出最近7天的数据:")
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        recent_data = exporter.export_complete_dataset(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        recent_filename = f"qdev_recent_7days_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        exporter.save_to_file(recent_data, recent_filename)
        print(f"   最近7天数据已导出到: {recent_filename}")
        
        print("\n=== JSON导出完成 ===")
        
    except Exception as e:
        print(f"导出错误: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
