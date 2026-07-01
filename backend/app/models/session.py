"""
会话与消息模型：对话管理系统的核心表
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, func
from app.core.database import Base


class Session(Base):
    """会话表 —— 每个用户可有多个对话会话"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_title = Column(String(256), default="新对话", comment="会话标题")
    status = Column(String(16), default="active", comment="状态: active/archived")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class Message(Base):
    """对话消息表 —— 记录每次问答的详细内容"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(16), nullable=False, comment="角色: user/assistant/system")
    content = Column(Text, nullable=False, comment="消息内容（支持 Markdown）")
    sources = Column(JSON, comment="引用来源 [{\"doc_name\":\"...\", \"section\":\"...\", \"page\":87}]")
    token_usage = Column(JSON, comment="token 用量 {\"prompt_tokens\":500,\"completion_tokens\":300}")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


class Feedback(Base):
    """问答反馈表 —— 用户对 AI 回答的点赞/点踩"""
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(String(8), nullable=False, comment="评价: up/down")
    reason = Column(String(256), comment="点踩原因")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
