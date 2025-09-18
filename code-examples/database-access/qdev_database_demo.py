#!/usr/bin/env python3
"""
Q Dev用户指标数据库直接访问Demo
方案1: 直接数据库访问 - 最简单的数据集成方案
"""

import mysql.connector
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class QDevMetricsDB:
    """Q Dev指标数据库访问类"""
    
    def __init__(self, host='<EC2-PUBLIC-IP>', port=3306, user='merico', password='merico', database='lake'):
        """初始化数据库连接配置"""
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
    
    def get_user_metrics_summary(self, connection_id: int = 1) -> pd.DataFrame:
        """获取用户指标汇总数据"""
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
            df = pd.read_sql(query, conn, params=[connection_id])
            return df
        finally:
            conn.close()
    
    def get_user_daily_data(self, connection_id: int = 1, 
                           start_date: Optional[str] = None, 
                           end_date: Optional[str] = None) -> pd.DataFrame:
        """获取用户日常数据"""
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
            df = pd.read_sql(query, conn, params=params)
            return df
        finally:
            conn.close()
    
    def get_user_detail(self, user_id: str, connection_id: int = 1) -> Dict:
        """获取特定用户的详细数据"""
        # 获取用户汇总数据
        summary_query = """
        SELECT * FROM _tool_q_dev_user_metrics
        WHERE connection_id = %s AND user_id = %s
        """
        
        # 获取用户日常数据
        daily_query = """
        SELECT * FROM _tool_q_dev_user_data
        WHERE connection_id = %s AND user_id = %s
        ORDER BY date DESC
        """
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            
            # 获取汇总数据
            cursor.execute(summary_query, [connection_id, user_id])
            summary = cursor.fetchone()
            
            # 获取日常数据
            cursor.execute(daily_query, [connection_id, user_id])
            daily_data = cursor.fetchall()
            
            return {
                'user_summary': summary,
                'daily_data': daily_data
            }
        finally:
            conn.close()
    
    def get_metrics_statistics(self, connection_id: int = 1) -> Dict:
        """获取指标统计信息"""
        query = """
        SELECT 
            COUNT(*) as total_users,
            SUM(total_inline_suggestions_count) as total_suggestions,
            SUM(total_inline_acceptance_count) as total_acceptances,
            AVG(acceptance_rate) as avg_acceptance_rate,
            SUM(total_inline_ai_code_lines) as total_ai_code_lines,
            MIN(first_date) as earliest_date,
            MAX(last_date) as latest_date
        FROM _tool_q_dev_user_metrics
        WHERE connection_id = %s
        """
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, [connection_id])
            return cursor.fetchone()
        finally:
            conn.close()
    
    def export_to_json(self, output_file: str = 'qdev_metrics_export.json') -> str:
        """导出数据为JSON格式"""
        # 获取所有数据
        summary_df = self.get_user_metrics_summary()
        daily_df = self.get_user_daily_data()
        statistics = self.get_metrics_statistics()
        
        # 组装导出数据
        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'total_users': len(summary_df),
                'data_source': 'DevLake MySQL Database'
            },
            'statistics': statistics,
            'user_metrics_summary': summary_df.to_dict('records'),
            'user_daily_data': daily_df.to_dict('records')
        }
        
        # 写入JSON文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str, ensure_ascii=False)
        
        return output_file

def main():
    """Demo主函数"""
    print("=== Q Dev用户指标数据库访问Demo ===\n")
    
    # 初始化数据库访问对象
    db = QDevMetricsDB()
    
    try:
        # 1. 获取用户指标汇总
        print("1. 用户指标汇总数据:")
        summary_df = db.get_user_metrics_summary()
        print(f"   找到 {len(summary_df)} 个用户")
        if not summary_df.empty:
            print("   用户列表:")
            for _, row in summary_df.iterrows():
                print(f"   - 用户ID: {row['user_id'][:8]}...")
                print(f"     建议数: {row['total_inline_suggestions_count']}")
                print(f"     接受数: {row['total_inline_acceptance_count']}")
                print(f"     接受率: {row['acceptance_rate']:.2%}")
                print(f"     AI代码行: {row['total_inline_ai_code_lines']}")
                print()
        
        # 2. 获取统计信息
        print("2. 整体统计信息:")
        stats = db.get_metrics_statistics()
        if stats:
            print(f"   总用户数: {stats['total_users']}")
            print(f"   总建议数: {stats['total_suggestions']}")
            print(f"   总接受数: {stats['total_acceptances']}")
            print(f"   平均接受率: {stats['avg_acceptance_rate']:.2%}")
            print(f"   总AI代码行: {stats['total_ai_code_lines']}")
            print(f"   数据时间范围: {stats['earliest_date']} 到 {stats['latest_date']}")
            print()
        
        # 3. 获取日常数据
        print("3. 用户日常数据:")
        daily_df = db.get_user_daily_data()
        print(f"   找到 {len(daily_df)} 条日常记录")
        if not daily_df.empty:
            print("   最近的记录:")
            for _, row in daily_df.head(3).iterrows():
                print(f"   - 日期: {row['date']}")
                print(f"     用户: {row['user_id'][:8]}...")
                print(f"     当日建议: {row['inline_suggestions_count']}")
                print(f"     当日接受: {row['inline_acceptance_count']}")
                print()
        
        # 4. 导出数据
        print("4. 导出数据到JSON文件:")
        export_file = db.export_to_json()
        print(f"   数据已导出到: {export_file}")
        
        # 5. 获取特定用户详情
        if not summary_df.empty:
            first_user_id = summary_df.iloc[0]['user_id']
            print(f"5. 用户详情示例 (用户ID: {first_user_id[:8]}...):")
            user_detail = db.get_user_detail(first_user_id)
            if user_detail['user_summary']:
                summary = user_detail['user_summary']
                print(f"   活跃天数: {summary['total_days']}")
                print(f"   总建议数: {summary['total_inline_suggestions_count']}")
                print(f"   日均建议数: {summary['avg_inline_suggestions_count']:.1f}")
                print(f"   日常记录数: {len(user_detail['daily_data'])}")
        
        print("\n=== Demo执行完成 ===")
        return True
        
    except mysql.connector.Error as e:
        print(f"数据库连接错误: {e}")
        return False
    except Exception as e:
        print(f"执行错误: {e}")
        return False

if __name__ == "__main__":
    main()
