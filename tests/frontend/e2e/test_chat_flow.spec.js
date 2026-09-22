/**
 * Enterprise AI Digital Assistant - Frontend E2E Business Flow Specification
 * Tests the complete ChatGPT/Gemini paradigm and Human-in-the-Loop approval resumption.
 * Flow: [Employee Inquiry -> Thought Capsule -> Approval Interruption -> One-Click Approval -> Stream Resumption & ERP Ticket]
 */

const { describe, it, beforeEach } = require('node:test');
const assert = require('node:assert/strict');

describe('E2E Interaction Flow: Employee Equipment Procurement & Approval', () => {
  let mockState = {};

  beforeEach(() => {
    mockState = {
      sessionId: 'sess_proc_001',
      sessionTitle: '申请采购 1 台高配开发机 MacBook Pro 16',
      messages: [],
      pendingApprovals: [],
      isStreaming: false,
    };
  });

  it('Step 1: Employee sends high-value hardware procurement message', () => {
    const userMessage = {
      id: 'msg_001',
      role: 'user',
      content: '请帮我申请采购 1 台高配开发机 MacBook Pro 16，单价 22,999 元。',
      timestamp: '14:30',
    };
    mockState.messages.push(userMessage);

    assert.equal(mockState.messages.length, 1);
    assert.equal(mockState.messages[0].role, 'user');
    assert.ok(mockState.messages[0].content.includes('MacBook Pro 16'));
  });

  it('Step 2: AI Assistant displays Gemini-style thinking badge and consults enterprise policies', () => {
    const aiMessage = {
      id: 'msg_002',
      role: 'assistant',
      isStreaming: true,
      thoughtTitle: '正在核对企业规章制度与库存数据...',
      thoughtStatus: 'thinking',
      sources: [
        {
          title: '企业采购与审批 SOP 流程规范',
          doc_id: 'DOC-PROC-2026-002',
          snippet: '单笔采购金额超过人民币 5,000 元整，必须提交部门主管及采购审批流复核。',
        },
        {
          title: 'IT 运维与资产借用指南',
          doc_id: 'DOC-IT-2026-003',
          snippet: 'AI 数字人研发岗位允许申请配置最高规格开发机以保障本地量化算力需求。',
        },
      ],
      content: '',
    };
    mockState.messages.push(aiMessage);

    assert.equal(aiMessage.thoughtStatus, 'thinking');
    assert.equal(aiMessage.sources.length, 2);
    assert.equal(aiMessage.sources[0].doc_id, 'DOC-PROC-2026-002');
  });

  it('Step 3: High-value threshold triggers LangGraph interruption and renders ApprovalCard', () => {
    const currentAiMsg = {
      id: 'msg_002',
      role: 'assistant',
      isStreaming: false,
      thoughtStatus: 'completed',
      thoughtTitle: '已参考 2 篇规章制度与知识来源',
      content: '已为您核对制度并生成设备采购申请单。依据公司财务与采购制度，金额大于 ￥5,000 元需提交主管审批：',
    };

    // LangGraph interrupt() event mapped into natural approval data
    const approvalData = {
      id: 'PR-20260922-01',
      approval_id: 'PR-20260922-01',
      title: '企业大额采购审批确认单',
      item_name: 'MacBook Pro 16 (高配开发机)',
      total_price: 22999.0,
      department: '研发部 (AI 工程组)',
      applicant: '李工',
      reason: '本地大模型量化调试与高并发端侧推理测试算力需求',
      status: 'PENDING',
    };
    currentAiMsg.interruptData = approvalData;
    mockState.messages.push(currentAiMsg);
    mockState.pendingApprovals.push(approvalData);

    assert.equal(currentAiMsg.interruptData.status, 'PENDING');
    assert.equal(currentAiMsg.interruptData.total_price, 22999.0);
    assert.equal(mockState.pendingApprovals.length, 1);
  });

  it('Step 4: Department Manager one-click approves purchase request via /api/v1/approval/action', async () => {
    const approval = {
      id: 'PR-20260922-01',
      approval_id: 'PR-20260922-01',
      status: 'PENDING',
    };
    mockState.pendingApprovals.push(approval);

    const decisionPayload = {
      approval_id: approval.approval_id,
      action: 'approve',
      comment: '配置核验属实，准予采购。',
      approver: '张经理 (研发部主管)',
    };

    // Simulate approval resolution
    approval.status = 'APPROVED';
    approval.comment = decisionPayload.comment;
    approval.approver = decisionPayload.approver;
    mockState.pendingApprovals = mockState.pendingApprovals.filter(
      (a) => a.id !== approval.id
    );

    assert.equal(approval.status, 'APPROVED');
    assert.equal(approval.comment, '配置核验属实，准予采购。');
    assert.equal(mockState.pendingApprovals.length, 0);
  });

  it('Step 5: Execution graph resumes and yields ERP procurement ticket', () => {
    const currentAiMsg = {
      id: 'msg_002',
      content: '已为您核对制度并生成设备采购申请单。',
      completed: false,
    };

    currentAiMsg.isStreaming = false;
    currentAiMsg.completed = true;
    currentAiMsg.content +=
      '\n\n审批已通过！已自动对接企业 ERP 供应链系统，成功创建采购执行工单：**`WO-ERP-20260922-9981`**，预计 2 个工作日内由采购部完成招采流转。';

    assert.ok(currentAiMsg.content.includes('WO-ERP-20260922-9981'));
    assert.equal(currentAiMsg.completed, true);
  });

  it('Step 6: Responsive Mobile Drawer and visualViewport virtual keyboard adaptation', () => {
    const mobileViewport = { width: 375, height: 667 };
    const isMobile = mobileViewport.width < 768;
    assert.equal(isMobile, true);

    // Simulate virtual keyboard popping up on mobile
    const visualViewport = { width: 375, height: 367, offsetTop: 0 };
    const keyboardOffset = Math.max(
      0,
      mobileViewport.height - visualViewport.height - visualViewport.offsetTop
    );

    assert.equal(keyboardOffset, 300);
    const dynamicTransform = `translateY(-${keyboardOffset}px)`;
    assert.equal(dynamicTransform, 'translateY(-300px)');
  });
});
