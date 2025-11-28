#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SillyTavern 聊天记录自动同步脚本
监控本地聊天文件夹，自动上传到 GitHub
"""

import os
import time
import json
import shutil
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess

# ==================== 配置区 ====================
# 你的 SillyTavern 聊天记录路径
SILLYTAVERN_CHATS_PATH = r"D:\SillyTavern\SillyTavern\data\default-user\chats"

# 本地 Git 仓库路径（用于存储同步的聊天记录）
LOCAL_REPO_PATH = r"D:\st-chats-backup"

# GitHub 仓库信息（需要你创建一个私有仓库）
GITHUB_REPO_URL = "https://github.com/YINGYING-745/st-chats-backup.git"  # 修改这里
GITHUB_TOKEN = ""  # 修改这里

# 同步间隔（秒）- 避免频繁提交
SYNC_INTERVAL = 300  # 5分钟同步一次
# ===============================================


class ChatSyncHandler(FileSystemEventHandler):
    """文件变化监控处理器"""
    
    def __init__(self, sync_manager):
        self.sync_manager = sync_manager
        self.last_sync_time = time.time()
    
    def on_modified(self, event):
        """文件修改时触发"""
        if event.is_directory:
            return
        
        # 只处理 .jsonl 文件
        if event.src_path.endswith('.jsonl'):
            current_time = time.time()
            # 防止频繁同步
            if current_time - self.last_sync_time > SYNC_INTERVAL:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检测到文件变化: {event.src_path}")
                self.sync_manager.sync_to_github()
                self.last_sync_time = current_time
    
    def on_created(self, event):
        """新文件创建时触发"""
        if not event.is_directory and event.src_path.endswith('.jsonl'):
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检测到新文件: {event.src_path}")
            time.sleep(2)  # 等待文件写入完成
            self.sync_manager.sync_to_github()
            self.last_sync_time = time.time()


class ChatSyncManager:
    """聊天记录同步管理器"""
    
    def __init__(self, source_path, repo_path, github_url, github_token):
        self.source_path = Path(source_path)
        self.repo_path = Path(repo_path)
        self.github_url = github_url
        self.github_token = github_token
        
        # 初始化本地仓库
        self.init_repo()
    
    def init_repo(self):
        """初始化本地 Git 仓库"""
        if not self.repo_path.exists():
            print(f"创建本地仓库目录: {self.repo_path}")
            self.repo_path.mkdir(parents=True, exist_ok=True)
            
            # 初始化 Git
            os.chdir(self.repo_path)
            subprocess.run(['git', 'init'], check=True)
            
            # 添加远程仓库（使用 token 认证）
            auth_url = self.github_url.replace('https://', f'https://{self.github_token}@')
            subprocess.run(['git', 'remote', 'add', 'origin', auth_url], check=True)
            
            print("本地仓库初始化完成")
        else:
            print(f"使用现有仓库: {self.repo_path}")
    
    def copy_chats(self):
        """复制聊天记录到本地仓库"""
        copied_count = 0
        
        # 遍历所有角色文件夹
        for character_folder in self.source_path.iterdir():
            if not character_folder.is_dir():
                continue
            
            # 目标文件夹
            target_folder = self.repo_path / character_folder.name
            target_folder.mkdir(exist_ok=True)
            
            # 复制所有 .jsonl 文件
            for chat_file in character_folder.glob('*.jsonl'):
                target_file = target_folder / chat_file.name
                
                # 只在文件不存在或已修改时复制
                if not target_file.exists() or \
                   chat_file.stat().st_mtime > target_file.stat().st_mtime:
                    shutil.copy2(chat_file, target_file)
                    copied_count += 1
        
        return copied_count
    
    def sync_to_github(self):
        """同步到 GitHub"""
        try:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始同步...")
            
            # 复制文件
            copied_count = self.copy_chats()
            
            if copied_count == 0:
                print("没有新的变化，跳过同步")
                return
            
            print(f"已复制 {copied_count} 个文件")
            
            # Git 操作
            os.chdir(self.repo_path)
            
            # 添加所有更改
            subprocess.run(['git', 'add', '.'], check=True)
            
            # 检查是否有更改
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True)
            
            if not result.stdout.strip():
                print("没有需要提交的更改")
                return
            
            # 提交
            commit_msg = f"Auto sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
            
            # 推送到 GitHub
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            
            print(f"✅ 同步成功！共 {copied_count} 个文件")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git 操作失败: {e}")
        except Exception as e:
            print(f"❌ 同步失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("SillyTavern 聊天记录自动同步脚本")
    print("=" * 60)
    print(f"监控目录: {SILLYTAVERN_CHATS_PATH}")
    print(f"本地仓库: {LOCAL_REPO_PATH}")
    print(f"同步间隔: {SYNC_INTERVAL} 秒")
    print("=" * 60)
    
    # 检查源目录是否存在
    if not Path(SILLYTAVERN_CHATS_PATH).exists():
        print(f"❌ 错误: 找不到 SillyTavern 聊天目录: {SILLYTAVERN_CHATS_PATH}")
        print("请检查配置区的路径设置")
        return
    
    # 创建同步管理器
    sync_manager = ChatSyncManager(
        SILLYTAVERN_CHATS_PATH,
        LOCAL_REPO_PATH,
        GITHUB_REPO_URL,
        GITHUB_TOKEN
    )
    
    # 首次同步
    print("\n执行首次同步...")
    sync_manager.sync_to_github()
    
    # 启动文件监控
    print("\n开始监控文件变化...")
    print("按 Ctrl+C 停止\n")
    
    event_handler = ChatSyncHandler(sync_manager)
    observer = Observer()
    observer.schedule(event_handler, SILLYTAVERN_CHATS_PATH, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止监控...")
        observer.stop()
    
    observer.join()
    print("程序已退出")


if __name__ == "__main__":
    main()
