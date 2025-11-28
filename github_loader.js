// GitHub 数据源配置
// 将此配置添加到 index.html 的 <script> 标签开头

const GITHUB_CONFIG = {
    // 你的 GitHub 用户名
    username: 'YINGYING-745',
    
    // 仓库名称
    repo: 'st-chats-backup',
    
    // 分支名称（通常是 main 或 master）
    branch: 'main',
    
    // GitHub Personal Access Token (可选，用于私有仓库)
    // 如果是公开仓库可以留空
    token: '',
    
    // 是否启用自动加载
    autoLoad: true,
    
    // 刷新间隔（毫秒），0 表示不自动刷新
    refreshInterval: 60000  // 每分钟检查一次
};

// GitHub API 加载函数
async function loadChatsFromGitHub() {
    try {
        console.log('从 GitHub 加载聊天记录...');
        
        const baseUrl = `https://api.github.com/repos/${GITHUB_CONFIG.username}/${GITHUB_CONFIG.repo}/contents`;
        const headers = {
            'Accept': 'application/vnd.github.v3+json'
        };
        
        // 如果配置了 token，添加认证
        if (GITHUB_CONFIG.token) {
            headers['Authorization'] = `token ${GITHUB_CONFIG.token}`;
        }
        
        // 获取仓库根目录内容
        const response = await fetch(`${baseUrl}?ref=${GITHUB_CONFIG.branch}`, { headers });
        
        if (!response.ok) {
            throw new Error(`GitHub API 请求失败: ${response.status}`);
        }
        
        const folders = await response.json();
        
        // 遍历所有角色文件夹
        for (const folder of folders) {
            if (folder.type !== 'dir') continue;
            
            const characterName = folder.name;
            
            // 获取角色文件夹中的聊天文件
            const chatFilesResponse = await fetch(folder.url, { headers });
            const chatFiles = await chatFilesResponse.json();
            
            // 处理每个聊天文件
            for (const file of chatFiles) {
                if (!file.name.endsWith('.jsonl')) continue;
                
                // 下载文件内容
                const fileResponse = await fetch(file.download_url);
                const content = await fileResponse.text();
                
                // 解析聊天记录
                const messages = parseChatContent(content);
                
                if (messages.length === 0) continue;
                
                // 生成唯一 ID
                const chatId = `${characterName}_${file.name}`;
                
                // 检查是否已存在
                const existing = await getChatFromDB(chatId);
                
                // 如果不存在或需要更新，保存到数据库
                if (!existing || file.sha !== existing.sha) {
                    const chatRecord = {
                        id: chatId,
                        name: `${characterName} - ${file.name.replace('.jsonl', '')}`,
                        characterName: characterName,
                        messages: messages,
                        sha: file.sha,  // 用于检测更新
                        timestamp: new Date(file.download_url).getTime()
                    };
                    
                    await saveChatToDB(chatRecord);
                    console.log(`已加载: ${chatRecord.name}`);
                }
            }
        }
        
        // 刷新聊天列表
        await refreshChatList();
        
        console.log('✅ GitHub 数据加载完成');
        
    } catch (error) {
        console.error('❌ 从 GitHub 加载失败:', error);
        alert(`从 GitHub 加载失败: ${error.message}\n请检查配置是否正确`);
    }
}

// 自动加载和刷新
window.addEventListener('DOMContentLoaded', async () => {
    if (GITHUB_CONFIG.autoLoad) {
        await loadChatsFromGitHub();
        
        // 设置定期刷新
        if (GITHUB_CONFIG.refreshInterval > 0) {
            setInterval(async () => {
                console.log('定期刷新 GitHub 数据...');
                await loadChatsFromGitHub();
            }, GITHUB_CONFIG.refreshInterval);
        }
    }
});

// 手动刷新按钮（添加到工具栏）
function addGitHubRefreshButton() {
    const toolbar = document.getElementById('toolbar');
    const refreshBtn = document.createElement('button');
    refreshBtn.className = 'btn';
    refreshBtn.innerHTML = '🔄 从 GitHub 刷新';
    refreshBtn.onclick = loadChatsFromGitHub;
    toolbar.appendChild(refreshBtn);
}

// 页面加载后添加刷新按钮
window.addEventListener('DOMContentLoaded', addGitHubRefreshButton);
