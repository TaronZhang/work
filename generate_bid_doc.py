#!/usr/bin/env python3
"""
Generate Package 1 bid document for 网络攻防红蓝军演训服务
Project: HF26-0236/01-03, Package 1: 攻防演练-实网攻防
Requirements: Zero deviation from tender, no company/product names
"""

from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
import datetime

doc = Document()

# ---- Page setup ----
for section in doc.sections:
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.17)
    section.right_margin = Cm(3.17)

style = doc.styles['Normal']
font = style.font
font.name = '宋体'
font.size = Pt(10.5)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
pf = style.paragraph_format
pf.line_spacing = 1.5
pf.space_before = Pt(0)
pf.space_after = Pt(0)

# Heading styles
for i in [1, 2, 3]:
    hs = doc.styles[f'Heading {i}']
    hf = hs.font
    hf.name = '黑体'
    hs.element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    hf.color.rgb = RGBColor(0, 0, 0)
    if i == 1:
        hf.size = Pt(16)
        hs.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        hs.paragraph_format.space_before = Pt(12)
        hs.paragraph_format.space_after = Pt(12)
    elif i == 2:
        hf.size = Pt(14)
        hs.paragraph_format.space_before = Pt(10)
        hs.paragraph_format.space_after = Pt(10)
    elif i == 3:
        hf.size = Pt(12)
        hs.paragraph_format.space_before = Pt(8)
        hs.paragraph_format.space_after = Pt(8)

def add_paragraph(t, style_name='Normal', bold=False, alignment=None, font_size=None, first_line_indent=True):
    """Add a paragraph with optional formatting."""
    if style_name == 'Normal' and first_line_indent and t and not t.startswith('（') and not t.startswith('注') and len(t) > 20:
        p = doc.add_paragraph(style=style_name)
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0.74)
    else:
        p = doc.add_paragraph(style=style_name)

    run = p.add_run(t)
    run.font.name = '宋体'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    if bold:
        run.bold = True
    if font_size:
        run.font.size = Pt(font_size)
    if alignment is not None:
        p.alignment = alignment
    return p

def add_heading_text(text, level=2):
    """Add a heading."""
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.name = '黑体'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        run.font.color.rgb = RGBColor(0, 0, 0)
    return h

def add_body(text):
    """Add body text with standard formatting."""
    return add_paragraph(text)

def add_table_with_style(headers, rows, col_widths=None):
    """Add a formatted table."""
    table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header row
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ''
        p = cell.paragraphs[0]
        run = p.add_run(header)
        run.bold = True
        run.font.name = '宋体'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        run.font.size = Pt(9)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Gray background
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="D9D9D9"/>')
        cell._element.get_or_add_tcPr().append(shading)

    # Data rows
    for r, row_data in enumerate(rows):
        for c, cell_text in enumerate(row_data):
            cell = table.rows[r + 1].cells[c]
            cell.text = ''
            p = cell.paragraphs[0]
            run = p.add_run(str(cell_text))
            run.font.name = '宋体'
            run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
            run.font.size = Pt(9)

    if col_widths:
        for i, width in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(width)

    doc.add_paragraph()  # spacing after table
    return table

# ===================================================================
# COVER PAGE
# ===================================================================
for _ in range(6):
    doc.add_paragraph()

add_paragraph('网络攻防红蓝军演训服务项目', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, font_size=22, first_line_indent=False)
add_paragraph('项目编号：HF26-0236/01-03', alignment=WD_ALIGN_PARAGRAPH.CENTER, font_size=14, first_line_indent=False)
add_paragraph('包件1：攻防演练-实网攻防', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, font_size=16, first_line_indent=False)

for _ in range(4):
    doc.add_paragraph()

add_paragraph('投 标 文 件', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, font_size=26, first_line_indent=False)

for _ in range(6):
    doc.add_paragraph()

add_paragraph('投标人：________________________________', alignment=WD_ALIGN_PARAGRAPH.CENTER, font_size=12, first_line_indent=False)
add_paragraph('日  期：2026年    月    日', alignment=WD_ALIGN_PARAGRAPH.CENTER, font_size=12, first_line_indent=False)

doc.add_page_break()

# ===================================================================
# TABLE OF CONTENTS placeholder
# ===================================================================
doc.add_heading('目  录', level=1)
add_paragraph('（投标文件具体内容详见后续各章节，目录从略）', first_line_indent=False)
doc.add_page_break()

# ===================================================================
# BUSINESS SECTION
# ===================================================================
doc.add_heading('商务部分', level=1)

# ---- 1. 投标函 ----
doc.add_heading('1. 投标函', level=2)
add_paragraph('投 标 函', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, font_size=14, first_line_indent=False)
add_paragraph('')
add_paragraph('致：公安部第三研究所')
add_paragraph('')
add_paragraph('根据贵方招标编号为 HF26-0236/01 的 网络攻防红蓝军演训服务（包件1：攻防演练-实网攻防）（项目名称）的招标文件，正式授权下述签字人_______________（姓名和职务）代表投标方（投标方的名称），提交下述投标文件正本一份，副本四份。投标文件包括以下内容：')
add_paragraph('')
add_paragraph('商务部分')
add_paragraph('1.   投标函')
add_paragraph('2.   开标一览表')
add_paragraph('3.   分项报价表')
add_paragraph('4.   法定代表人（负责人）授权委托书')
add_paragraph('5.   中小企业声明函、残疾人福利性单位声明函')
add_paragraph('6.   商务技术条款偏离表')
add_paragraph('7.   服务人员配置方案及拟投入本项目的人员表')
add_paragraph('8.   拟投入本项目的主要人员情况表（附相关证书复印件并加盖公章）')
add_paragraph('9.   近三年完成的类似项目情况表(附合同复印件并加盖公章)')
add_paragraph('10.  正在进行的和新承接的项目情况表')
add_paragraph('11.  投标人基本情况简介')
add_paragraph('12.  提供参加政府采购活动前3年内在经营活动中没有重大违法记录的书面声明')
add_paragraph('13.  提供营业执照（三证合一或五证合一）等证明文件')
add_paragraph('14.  财务状况及税收、社会保障资金缴纳情况声明函')
add_paragraph('15.  供应商不得存在下列情形之一：被责令停业的；被暂停或取消投标资格的；财产被接管或冻结的；在最近三年内有骗取中标或严重违约的；在投标过程中因重大违规被采购人处罚的。提供承诺函')
add_paragraph('16.  不参与围标串标承诺书')
add_paragraph('17.  其他资料表（招标文件未要求，投标人认为应提供的相关资料）')
add_paragraph('')
add_paragraph('技术部分')
add_paragraph('包件一')
add_paragraph('1.  针对本项目的整体服务方案（包括但不限于：重难点分析及应对措施等、信息收集方案、线上线下攻防方案、成果汇报方案等）')
add_paragraph('2.  质量承诺及保证体系、措施')
add_paragraph('3.  安全保密措施、保密管理制度、保密协议承诺及模板')
add_paragraph('4.  应急响应能力（包括但不限于应急响应方案、应急响应时间承诺和应急响应团队名单及联系方式等）')
add_paragraph('')
add_paragraph('据此函，供应商兹宣布同意如下：')
add_paragraph('')
add_paragraph('1. 按招标文件规定，我方的报价总价为（大写）包件一：_______________元人民币。')
add_paragraph('2. 已缴纳投标保证金，金额为包件一：_______________元人民币。')
add_paragraph('3. 我方已详细研究了全部招标文件，包括招标文件的澄清和修改文件（如果有的话）、参考资料及有关附件，我们已完全理解并接受招标文件的各项规定和要求，对招标文件的合理性、合法性不再有异议。')
add_paragraph('4. 投标文件有效期为自递交投标文件截止之日起 90 日。')
add_paragraph('5. 如我方中标，投标文件将作为本项目合同的组成部分，直至合同履行完毕止均保持有效，我方将按招标文件及政府采购法律、法规的规定，承担完成合同的全部责任和义务。')
add_paragraph('6. 我方同意向贵方提供贵方可能进一步要求的与本项目有关的一切证据或资料。')
add_paragraph('7. 我方完全理解贵方不一定要接受最低报价的投标或其他任何响应。')
add_paragraph('8. 为便于贵方公正、择优地确定中标供应商及其报价货物和相关服务，我方就本次投标有关事项郑重声明如下：')
add_paragraph('（1）我方向贵方提交的所有投标文件、资料都是准确的和真实的；')
add_paragraph('（2）以上事项如有虚假或隐瞒，我方愿意承担一切后果，并不再寻求任何旨在减轻或免除法律责任的辩解。')
add_paragraph('')
add_paragraph('公司地址：________________________________________')
add_paragraph('公司电话：________________  传真：________________  邮编：________________')
add_paragraph('纳税人识别号：________________________________________')
add_paragraph('开户银行：________________________________________')
add_paragraph('银行账号：________________________________________')
add_paragraph('投标人授权代表姓名、职务（印刷体）：________________________________________')
add_paragraph('投标人名称（加盖企业公章）：________________________________________')
add_paragraph('投标人授权代表签字：________________')
add_paragraph('日      期：        年      月      日')

doc.add_page_break()

# ---- 2. 开标一览表 ----
doc.add_heading('2. 开标一览表', level=2)
add_paragraph('附件2  开标一览表（包件一）', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=False)

add_table_with_style(
    ['项目名称', '服务期限', '项目报价（小写）'],
    [['网络攻防红蓝军演训服务\n包件1：攻防演练-实网攻防', '自合同签订之日起一年', '']]
)
add_paragraph('项目报价（大写）：________________________________________', first_line_indent=False)
add_paragraph('开具发票税点：________________________________________', first_line_indent=False)
add_paragraph('')
add_paragraph('投标人名称：________________________    招标编号：HF26-0236/01')
add_paragraph('货币单位：人民币元')
add_paragraph('')
add_paragraph('投标人授权代表签字：________________')
add_paragraph('（加盖企业公章）')
add_paragraph('日   期：________________')

doc.add_page_break()

# ---- 3. 分项报价表 ----
doc.add_heading('3. 分项报价表', level=2)
add_paragraph('附件3  分项报价表', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=False)
add_paragraph('')

# Detailed cost breakdown table
add_table_with_style(
    ['序号', '服务内容', '工作项', '预计工作量（人月）', '单价（元/人月）', '合价（元）', '备注'],
    [
        ['1', '信息收集', '资产探测、信息收集、暴露面收集', '6', '', '', ''],
        ['2', '线上攻防', '漏洞扫描、漏洞利用、权限维持', '10', '', '', ''],
        ['3', '线下攻防', '资产扫描、权限维持、横向攻击', '10', '', '', ''],
        ['4', '成果汇报', '成果总结、整改建议、汇报材料', '4', '', '', ''],
        ['', '合计', '', '30', '', '', ''],
    ]
)

add_paragraph('投标人名称：________________________    招标编号：HF26-0236')
add_paragraph('货币单位：人民币元')
add_paragraph('')
add_paragraph('注：所报费用应包含整个项目过程中可能发生的所有费用。投标人在投标报价时必须充分考虑本项目所需要求，如果在报价中有缺项和漏项，则将被认为该项的价格已经包含在其他项中。采购人在签订合同的时候，不会对投标人缺漏项的金额给予补偿。')
add_paragraph('')
add_paragraph('投标人授权代表签字：________________')
add_paragraph('（加盖企业公章）')
add_paragraph('日   期：________________')

doc.add_page_break()

# ---- 4. 法定代表人授权委托书 ----
doc.add_heading('4. 法定代表人（负责人）授权委托书', level=2)
add_paragraph('法定代表人（负责人）证明书', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=False)
add_paragraph('')
add_paragraph('_______________先生/女士现担任_______________职务，负责全面工作，为我单位的法定代表人。特此证明。')
add_paragraph('')
add_paragraph('投标人全称：________________________')
add_paragraph('公章（盖章）')
add_paragraph('日期：________________')
add_paragraph('')
add_paragraph('法定代表人（负责人）代表授权书', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=False)
add_paragraph('')
add_paragraph('本授权书声明：')
add_paragraph('（公司名称）法人代表_______________（姓名）经合法授权，特代表本公司（以下称"投标人"）任命：_______________（姓名）为正式的合法代理人，并授权该代理人在有关 网络攻防红蓝军演训服务（包件1：攻防演练-实网攻防）（项目名称）的投标工作中，以投标人的名义签署投标文件、进行合同谈判、签署合同和全权处理招标活动中的一切事宜。')
add_paragraph('')
add_paragraph('特签字如下，以资证明。')
add_paragraph('')
add_paragraph('法定代表人（负责人）签字或盖章：________________')
add_paragraph('代理人签字：________________')
add_paragraph('投标人公章（盖章）')
add_paragraph('地        点：________________________')
add_paragraph('时        间：________________________')
add_paragraph('')
add_paragraph('注：请在投标文件中代理人身份证（正反面）复印件加盖公章，并在开标当天带好有效身份证件。')

doc.add_page_break()

# ---- 5. 中小企业声明函 ----
doc.add_heading('5. 中小企业声明函、残疾人福利性单位声明函', level=2)
add_paragraph('附件5-1  中小企业声明函（工程、服务）', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=False)
add_paragraph('')
add_paragraph('本公司（联合体）_______________郑重声明，根据《政府采购促进中小企业发展管理办法》（财库﹝2020﹞46号）的规定，本公司（联合体）_______________参加 公安部第三研究所（单位名称）的 网络攻防红蓝军演训服务（包件1：攻防演练-实网攻防）（项目名称）采购活动，工程的施工单位全部为符合政策要求的中小企业（或者：服务全部由符合政策要求的中小企业承接）。相关企业（含联合体中的中小企业、签订分包意向协议的中小企业）的具体情况如下：')
add_paragraph('')
add_paragraph('1. 网络攻防红蓝军演训服务（包件1：攻防演练-实网攻防）（标的名称），属于（软件和信息技术服务业）；承建（承接）企业为_______________（企业名称），从业人员____人，营业收入为____万元，资产总额为____万元，属于_______________（中型企业、小型企业、微型企业）；')
add_paragraph('')
add_paragraph('以上企业，不属于大企业的分支机构，不存在控股股东为大企业的情形，也不存在与大企业的负责人为同一人的情形。')
add_paragraph('本企业对上述声明内容的真实性负责。如有虚假，将依法承担相应责任。')
add_paragraph('')
add_paragraph('企业名称（盖章）：________________')
add_paragraph('日期：________________')
add_paragraph('')
add_paragraph('注：从业人员、营业收入、资产总额填报上一年度数据，无上一年度数据的新成立企业可不填报。')
add_paragraph('')
add_paragraph('附件5-2  残疾人福利性单位声明函', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=False)
add_paragraph('')
add_paragraph('本单位郑重声明，根据《财政部 民政部 中国残疾人联合会关于促进残疾人就业政府采购政策的通知》（财库〔2017〕141号）的规定，本单位安置残疾人____人，占本单位在职职工人数比例____%，符合残疾人福利性单位条件，且本单位参加单位的项目采购活动提供本单位制造的货物（由本单位承担工程/提供服务），或者提供其他残疾人福利性单位制造的货物（不包括使用非残疾人福利性单位注册商标的货物）。')
add_paragraph('本单位对上述声明的真实性负责。如有虚假，将依法承担相应责任。')
add_paragraph('')
add_paragraph('单位名称（盖章）：________________')
add_paragraph('日   期：________________')
add_paragraph('')
add_paragraph('如投标人不符合残疾人福利性单位条件，无需填写本声明。')

doc.add_page_break()

# ---- 6. 商务技术条款偏离表 ----
doc.add_heading('6. 商务技术条款偏离表', level=2)

# 商务条款偏离表
add_paragraph('附件6-3  商务条款偏离表', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=False)
add_paragraph('投标人名称：________________________')
add_paragraph('项目编号：HF26-0236/01')
add_paragraph('货币单位：元（人民币）')
add_paragraph('')

add_table_with_style(
    ['序号', '商务偏离类型\n(正负偏离)', '商务偏离的文档章节号\n及页号', '商务偏离的主要内容说明', '备注'],
    [['', '全部满足', '', '投标人完全响应招标文件所有商务条款要求，无偏离', '']]
)

add_paragraph('注：对于未列出的偏离内容视同供应商已完全接受招标文件的要求。我公司在此确认，对招标文件所有商务条款全部满足，无任何负偏离。')
add_paragraph('')
add_paragraph('投标人授权代表签字：________________')
add_paragraph('（加盖企业公章）')
add_paragraph('日   期：________________')
add_paragraph('')

# 技术条款偏离表
add_paragraph('附件6-4  技术条款偏离表', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=False)
add_paragraph('投标人名称：________________________')
add_paragraph('项目编号：HF26-0236/01')
add_paragraph('货币单位：元（人民币）')
add_paragraph('')

add_table_with_style(
    ['序号', '技术偏离类型\n(正负偏离)', '技术偏离的文档章节号\n及页号', '技术偏离的主要内容说明', '备注'],
    [['', '全部满足', '', '投标人完全响应招标文件所有技术条款要求，无偏离', '']]
)

add_paragraph('注：对于未列出的偏离内容视同供应商已完全接受招标文件的要求。我公司在此确认，对招标文件所有技术条款全部满足，无任何负偏离。')
add_paragraph('')
add_paragraph('投标人授权代表签字：________________')
add_paragraph('（加盖企业公章）')
add_paragraph('日   期：________________')

doc.add_page_break()

# ---- 7. 服务人员配置方案 ----
doc.add_heading('7. 服务人员配置方案及拟投入本项目的人员表', level=2)
add_paragraph('（详见技术部分人员配备方案，此处附人员表）', first_line_indent=False)
add_paragraph('')

add_table_with_style(
    ['序号', '姓  名', '职务', '职称及资格证书', '主要资历、经验及承担过的项目'],
    [
        ['1', '', '项目经理\n（高级人员）', '', ''],
        ['2', '', '高级攻防工程师\n（中级人员）', '', ''],
        ['3', '', '攻防工程师\n（初级人员）', '', ''],
        ['4', '', '攻防工程师\n（初级人员）', '', ''],
    ]
)

add_paragraph('注：投标人应将表列人员的资历情况填写并附相关资质证书及证明复印件并加盖公章。')
add_paragraph('')
add_paragraph('投标人授权代表签字：________________')
add_paragraph('（加盖企业公章）')
add_paragraph('日   期：________________')

doc.add_page_break()

# ---- 8-11 to be continued - concise versions ----

# ---- 8. 拟投入本项目的主要人员情况表 ----
doc.add_heading('8. 拟投入本项目的主要人员情况表', level=2)
add_paragraph('（附相关证书复印件并加盖公章）', first_line_indent=False)
add_paragraph('')

for idx in range(1, 5):
    add_paragraph(f'主要人员情况表（{idx}）', bold=True, first_line_indent=False)
    add_table_with_style(
        ['项目', '内容', '项目', '内容', '项目', '内容'],
        [
            ['姓    名', '', '年    龄', '', '技术职务', ''],
            ['职    务', '', '本合同中拟任职务', '', '为申请人服务时间', ''],
            ['学    历', '', '', '', '', ''],
            ['相关职业资格', '', '', '取得职业资格时间', '', ''],
        ]
    )
    add_paragraph('2. 经    历', bold=True, first_line_indent=False)
    add_table_with_style(
        ['年    份', '负责过的主要项目（类型、金额）', '负责过的主要项目（类型、金额）', '该项目中任职', '该项目中任职', '备    注'],
        [['', '', '', '', '', '']]
    )
    add_paragraph('')
    add_paragraph('备注：以上信息均是真实有效的。')
    add_paragraph('')

add_paragraph('投标人授权代表签字：________________  （加盖企业公章）')
add_paragraph('日   期：________________')

doc.add_page_break()

# ---- 9. 近三年完成的类似项目情况表 ----
doc.add_heading('9. 近三年完成的类似项目情况表', level=2)
add_paragraph('（附合同复印件加盖公章）', first_line_indent=False)
add_paragraph('')

add_table_with_style(
    ['项目序号', '1', '2', '3', '......'],
    [
        ['项目名称', '', '', '', ''],
        ['项目所在地', '', '', '', ''],
        ['项目采购人名称', '', '', '', ''],
        ['项目采购人地址', '', '', '', ''],
        ['项目采购人电话', '', '', '', ''],
        ['合同价格', '', '', '', ''],
        ['开始日期', '', '', '', ''],
        ['完成日期', '', '', '', ''],
        ['项目负责人', '', '', '', ''],
        ['备注（用户反映）', '', '', '', ''],
    ]
)

add_paragraph('备注：各单位可根据各自的项目数量，调整表单的列数。')
add_paragraph('')
add_paragraph('投标人授权代表签字：________________')
add_paragraph('（加盖企业公章）')
add_paragraph('日   期：________________')

doc.add_page_break()

# ---- 10. 正在进行的和新承接的项目情况表 ----
doc.add_heading('10. 正在进行的和新承接的项目情况表', level=2)
add_paragraph('')

add_table_with_style(
    ['项目序号', '1', '2', '3', '......'],
    [
        ['项目名称', '', '', '', ''],
        ['项目所在地', '', '', '', ''],
        ['项目采购人名称', '', '', '', ''],
        ['项目采购人地址', '', '', '', ''],
        ['项目采购人电话', '', '', '', ''],
        ['签约合同价', '', '', '', ''],
        ['开始日期', '', '', '', ''],
        ['完成日期', '', '', '', ''],
        ['项目经理', '', '', '', ''],
        ['备注（用户反映）', '', '', '', ''],
    ]
)

add_paragraph('备注：各单位可根据各自的项目数量，调整表单的列数。')
add_paragraph('')
add_paragraph('投标人授权代表签字：________________')
add_paragraph('（加盖企业公章）')
add_paragraph('日   期：________________')

doc.add_page_break()

# ---- 11. 投标人基本情况简介 ----
doc.add_heading('11. 投标人基本情况简介', level=2)
add_paragraph('（一）基本情况：', bold=True, first_line_indent=False)
add_paragraph('1、单位名称：________________________')
add_paragraph('2、地址：________________________')
add_paragraph('3、邮编：________________________')
add_paragraph('4、电话/传真：________________________')
add_paragraph('5、成立日期或注册日期：________________________')
add_paragraph('6、行业类型：软件和信息技术服务业')
add_paragraph('')
add_paragraph('（二）基本经济指标（到上年度12月31日止）：', bold=True, first_line_indent=False)
add_paragraph('1、实收资本：________________________')
add_paragraph('2、资产总额：________________________')
add_paragraph('3、负债总额：________________________')
add_paragraph('4、营业收入：________________________')
add_paragraph('5、净利润：________________________')
add_paragraph('6、上交税收：________________________')
add_paragraph('7、在册人数：________________________')
add_paragraph('')
add_paragraph('（三）其他情况：', bold=True, first_line_indent=False)
add_paragraph('1、专业人员分类及人数：________________________')
add_paragraph('2、企业资质证书情况：________________________')
add_paragraph('3、其他需要说明的情况：________________________')
add_paragraph('')
add_paragraph('我方承诺上述情况是真实、准确的，我方同意根据招标人进一步要求出示有关资料予以证实。')
add_paragraph('')
add_paragraph('投标人授权代表签字：________________')
add_paragraph('（加盖企业公章）')
add_paragraph('日   期：________________')

doc.add_page_break()

# ---- 12. 无重大违法记录声明 ----
doc.add_heading('12. 提供参加政府采购活动前3年内在经营活动中没有重大违法记录的书面声明', level=2)
add_paragraph('')
add_paragraph('声  明', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, font_size=14, first_line_indent=False)
add_paragraph('')
add_paragraph('我单位参加 网络攻防红蓝军演训服务（包件1：攻防演练-实网攻防）（项目名称）招标，郑重声明承诺满足以下条件：')
add_paragraph('')
add_paragraph('一、具有独立承担民事责任的能力；')
add_paragraph('二、具有良好的商业信誉和健全的财务会计制度；')
add_paragraph('三、具有履行合同所必需的设备和专业技术能力；')
add_paragraph('四、具有依法缴纳税收和社会保障资金的良好记录；')
add_paragraph('五、参加政府采购活动前3年内在经营活动中没有重大违法记录；')
add_paragraph('六、法律、行政法规规定的其他条件；')
add_paragraph('七、在本项目中提供的资料均真实、合法、有效。')
add_paragraph('')
add_paragraph('我方声明如违反上述承诺，自愿承担相应的法律后果。')
add_paragraph('')
add_paragraph('特此声明！')
add_paragraph('')
add_paragraph('投标人法定名称和地址、邮编：________________________________')
add_paragraph('电话：____________________    传真：____________________')
add_paragraph('投标人法定代表人（负责人）或授权代表签字或盖章：________________')
add_paragraph('日期：________________')
add_paragraph('投标人盖章：________________')

doc.add_page_break()

# ---- 13. 营业执照 ----
doc.add_heading('13. 提供营业执照（三证合一或五证合一）等证明文件', level=2)
add_paragraph('（此处附营业执照副本复印件并加盖公章）', first_line_indent=False)

doc.add_page_break()

# ---- 14. 财务状况声明函 ----
doc.add_heading('14. 财务状况及税收、社会保障资金缴纳情况声明函', level=2)
add_paragraph('')
add_paragraph('我方（供应商名称）符合《中华人民共和国政府采购法》第二十二条第一款第（二）项、第（四）项规定条件，具体包括：')
add_paragraph('1. 具有健全的财务会计制度；')
add_paragraph('2. 有依法缴纳税收和社会保障资金的良好记录。')
add_paragraph('特此声明。')
add_paragraph('')
add_paragraph('我方对上述声明的真实性负责。如有虚假，将依法承担相应责任。')
add_paragraph('')
add_paragraph('供应商名称（公章）：________________')
add_paragraph('日期：________________')

doc.add_page_break()

# ---- 15. 承诺函 ----
doc.add_heading('15. 供应商承诺函', level=2)
add_paragraph('（供应商不得存在下列情形之一：被责令停业的；被暂停或取消投标资格的；财产被接管或冻结的；在最近三年内有骗取中标或严重违约的；在投标过程中因重大违规被采购人处罚的。提供承诺函）', first_line_indent=False)
add_paragraph('')
add_paragraph('致：公安部第三研究所', first_line_indent=False)
add_paragraph('')
add_paragraph('我单位作为 网络攻防红蓝军演训服务（包件1：攻防演练-实网攻防）（项目名称）的投标人，在此郑重承诺：')
add_paragraph('')
add_paragraph('一、我单位不存在被责令停业的情形；')
add_paragraph('二、我单位不存在被暂停或取消投标资格的情形；')
add_paragraph('三、我单位不存在财产被接管或冻结的情形；')
add_paragraph('四、我单位在最近三年内不存在骗取中标或严重违约的情形；')
add_paragraph('五、我单位在投标过程中不存在因重大违规被采购人处罚的情形。')
add_paragraph('')
add_paragraph('以上承诺如有不实，我单位自愿承担由此引起的一切法律责任和后果。')
add_paragraph('')
add_paragraph('投标人名称（加盖公章）：________________')
add_paragraph('法定代表人或授权代表签字：________________')
add_paragraph('日期：________________')

doc.add_page_break()

# ---- 16. 不参与围标串标承诺书 ----
doc.add_heading('16. 不参与围标串标承诺书', level=2)
add_paragraph('')
add_paragraph('致：公安部第三研究所', first_line_indent=False)
add_paragraph('')
add_paragraph('本人作为经授权的投标人代表，清楚知晓我单位参加贵所项目投标活动，对以下事项作出郑重承诺：')
add_paragraph('一、我单位和我本人遵循公开、公平、公正、诚实守信的原则，依法依规参与本项目竞标。')
add_paragraph('二、我单位和我本人在本项目招标投标活动中，未参与围标串标。')
add_paragraph('三、我单位如被查实在本项目招标投标活动中存在围标串标的，递交投标文件行为作为实施串通投标违法行为的关键环节，我单位和我本人愿意承担相应的责任。')
add_paragraph('')
add_paragraph('')
add_paragraph('投标单位公章：')
add_paragraph('')
add_paragraph('投标单位法定代表人签名（签章）：________________')
add_paragraph('')
add_paragraph('投标单位被授权代表签名：________________')
add_paragraph('')
add_paragraph('日期：      年      月      日')

doc.add_page_break()

# ---- 17. 其他资料表 ----
doc.add_heading('17. 其他资料表', level=2)
add_paragraph('（招标文件未要求，投标人认为应提供的相关资料）', first_line_indent=False)
add_paragraph('')
add_paragraph('以下提供投标人相关资质证书、荣誉证书及其他补充材料（如有），作为投标文件补充部分，供评审专家参考。', first_line_indent=False)

doc.add_page_break()

# ===================================================================
# TECHNICAL SECTION - 包件一
# ===================================================================
doc.add_heading('技术部分', level=1)
doc.add_heading('包件一：攻防演练-实网攻防', level=2)

# ================================================================
# 1. 针对本项目的整体服务方案
# ================================================================
doc.add_heading('1. 针对本项目的整体服务方案', level=2)

# --- 1.1 重难点分析及应对措施 ---
add_heading_text('1.1 重难点分析及应对措施', level=3)

add_paragraph('本项目为公安部第三研究所委托的网络攻防红蓝军演训服务，包件一聚焦实网攻防演练。实网攻防演练是对真实网络环境的对抗性安全测试，涉及信息收集、互联网突破、内网渗透、横向移动、成果汇报等多个环节。结合本项目的服务要求与金融行业攻防演练的特点，我公司对以下重点难点进行深入分析，并提出针对性的应对措施。')

add_paragraph('')
add_paragraph('重点难点一：大型机构互联网资产暴露面广，信息收集与攻击面测绘难度大', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('分析：', bold=True, first_line_indent=False)
add_paragraph('大型金融机构通常拥有庞大的互联网资产体系，涵盖官方网站、网上银行、手机银行APP、微信小程序、支付宝小程序、公众号、API接口、云上资产、第三方合作平台、分支机构子域名、邮件系统、VPN接入点等各类互联网暴露面。资产数量多、类型复杂、管理分散，攻击者视角下的完整资产测绘工作难度极高。同时，金融机构的信息系统存在频繁的上线、变更、下线等动态变化，攻击面也在不断演变。此外，部分资产可能未纳入统一的IT资产管理，形成"影子IT"资产，这些资产往往是最容易被攻击者利用的薄弱环节。攻击者可以通过员工邮箱账号泄露、代码仓库泄露、云存储配置不当等渠道获取敏感信息，进一步扩大攻击面。')

add_paragraph('')
add_paragraph('应对措施：', bold=True, first_line_indent=False)
add_paragraph('（1）多维度资产探测：采用主动扫描与被动收集相结合的方式，运用多种资产扫描引擎对目标单位的域名、IP段、证书信息进行交叉关联分析，建立完整的互联网资产图谱。主动扫描覆盖全端口、全协议（TCP/UDP），被动收集包括DNS解析记录、SSL证书透明度日志（Certificate Transparency Logs）、搜索引擎缓存、公共数据源（如Shodan、Censys、FOFA、ZoomEye等）。')
add_paragraph('（2）资产分类与优先级排序：按照资产类型（Web应用、API接口、移动端、云服务、物联网设备等）、业务重要性（核心业务系统、一般业务系统、测试系统）、暴露程度（公网直接暴露、VPN后暴露）进行分类分级，优先对关键业务系统和高风险资产进行深度信息收集。')
add_paragraph('（3）社工信息收集：通过开源情报（OSINT）手段，系统收集目标单位的组织架构、分支机构信息、供应链关系、员工信息（公开渠道）、业务线分布、合作厂商信息等，为后续的定向社工攻击提供情报支撑。重点关注高管及IT运维人员的社交媒体信息、技术论坛发言、开源代码提交记录等。')
add_paragraph('（4）泄露信息检测：对暗网、黑客论坛、代码托管平台（GitHub、GitLab、Gitee等）、文库类网站、网盘等渠道进行持续监测，检测是否存在目标单位的源代码泄露、配置文件泄露、数据库备份泄露、员工账号密码泄露等安全风险。')
add_paragraph('（5）暴露面持续监控：建立暴露面变化监控机制，在攻防演练期间持续跟踪目标单位互联网资产的新增、变更情况，及时发现新暴露的攻击面，确保攻击方始终保持对目标环境的完整认知。')

add_paragraph('')
add_paragraph('重点难点二：攻防演练中权限维持与横向移动的隐蔽性挑战', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('分析：', bold=True, first_line_indent=False)
add_paragraph('在实网攻防演练中，攻击方在获取初始入口后，如何在目标环境中保持持久化访问权限，并在不被安全监控系统发现的情况下实现横向移动，是决定攻击链路深度和成果质量的关键。大型金融机构通常部署了完备的安全监控体系，包括但不限于：终端检测与响应平台（EDR）、网络流量分析系统（NTA）、安全信息和事件管理系统（SIEM）、主机入侵检测系统（HIDS）、欺骗防御系统（蜜罐）等。这些安全设备会对异常进程、异常网络连接、异常登录行为、敏感命令执行等进行实时监控和告警。攻击方在传统渗透测试中常用的工具和行为模式（如Mimikatz、PsExec、WMI、计划任务、注册表Run键等）极易被安全设备检测和拦截。此外，金融行业网络的区域隔离策略（DMZ区、内网办公区、核心业务区、生产网段等）较为严格，跨区域访问受到ACL策略、防火墙规则、网络准入控制等多重限制，横向移动的技术难度和被发现的风险均显著增加。')

add_paragraph('')
add_paragraph('应对措施：', bold=True, first_line_indent=False)
add_paragraph('（1）定制化攻击工具：针对目标环境的防护特点，在演练准备阶段进行充分的工具定制与免杀处理。根据前期信息收集阶段获取的目标安全设备清单及版本信息，针对性开发或改造攻击载荷与工具，规避目标环境的已知检测特征。所有攻击工具在使用前均经过本地测试环境的对抗验证，确保在目标安全体系下的可用性和隐蔽性。')
add_paragraph('（2）合法工具利用（Living off the Land）：优先使用目标系统自带的合法管理工具和脚本环境（如PowerShell、WMI、Certutil、Bitsadmin、Mshta、CMSTP、Regsvr32等）进行渗透操作，将攻击行为伪装为正常的系统管理活动。充分利用Windows和Linux系统内置的功能组件，减少对外部工具的依赖，降低被安全设备标记为异常行为的概率。')
add_paragraph('（3）多通道C2通信：建立多层次的命令与控制（C2）通信通道，采用HTTPS、DNS隧道、ICMP隧道、WebSocket等多种协议进行回联。C2通信流量模拟正常业务流量特征，如模仿HTTP API调用、Web浏览器行为等。配置流量整形策略，控制通信频率和数据量，避免在流量层面产生异常特征。同时建立备用C2通道冗余机制，确保主通道被阻断后能快速切换。')
add_paragraph('（4）权限维持隐蔽化：建立多层次的权限维持体系，包括系统层面（服务、计划任务、WMI事件订阅、DLL劫持、COM劫持）、Web层面（Webshell、代码注入、计划任务接口）、网络层面（VPN账号、SSH隧道、反向代理）等多种手段的组合。优先选择不落盘、内存执行的权限维持方式，定期轮换权限维持机制，避免单一后门被清除后失去所有访问权限。')
add_paragraph('（5）横向移动精细化：在进行横向移动前，充分进行内网信息收集，包括但不限于网络拓扑探测、域环境信息收集（域控、域成员、域信任关系）、凭证收集（Kerberos票据、明文密码哈希、浏览器保存密码、配置文件中的凭证等）、应用系统信息收集（数据库、中间件、运维平台、代码仓库、知识管理系统等）。根据收集到的信息制定精确的横向移动路径，优先选择高价值目标（域控制器、核心数据库服务器、运维管理平台、代码仓库、配置管理数据库等），避免盲目扫描和暴力尝试，减少横向移动过程中的异常流量和告警。')

add_paragraph('')
add_paragraph('重点难点三：攻防成果的有效总结与整改建议的可落地性', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('分析：', bold=True, first_line_indent=False)
add_paragraph('攻防演练的最终价值不仅在于攻击成果本身，更在于通过攻击视角发现防御体系的薄弱环节，为后续安全建设提供方向性指引。然而，攻击方与防守方之间存在天然的信息不对称：攻击方掌握完整的攻击链路和技术细节，但可能不了解防守方的安全体系架构和运营流程；防守方了解自身的安全建设现状，但可能无法从单次攻击的角度全面理解防御漏洞的根本原因。如果成果汇报仅停留在漏洞罗列和技术炫耀层面，不能从防御者的视角提供切实可行的整改建议，则攻防演练的实际价值将大打折扣。此外，大型金融机构的安全整改涉及多部门、多系统的协调，整改建议需要充分考虑业务连续性、系统兼容性、合规要求等多重约束条件。')

add_paragraph('')
add_paragraph('应对措施：', bold=True, first_line_indent=False)
add_paragraph('（1）攻击链路全景还原：对每条成功的攻击路径进行完整回溯，绘制从外部信息收集→初始入侵→权限提升→横向移动→目标达成的全链路攻击图（Attack Graph），清晰标注每个攻击阶段所利用的漏洞、使用的技术手段、突破的安全防线、触达的关键资产。通过可视化的方式直观呈现攻击全貌，使防守方能够全面理解攻击者的思路和手法。')
add_paragraph('（2）攻击根因深度分析：对每个成功攻击节点的根本原因进行深度分析，从技术层面（如漏洞未修复、配置不当、权限过大、网络隔离不足）、管理层面（如资产管理缺失、变更管理不规范、安全策略不完善）、人员层面（如安全意识不足、应急响应不及时）等多个维度进行归因，帮助防守方从根本上理解安全问题的深层原因。')
add_paragraph('（3）分层分级整改建议：根据漏洞的危害程度、利用难度、影响范围对整改建议进行分级（紧急、高、中、低），根据整改措施的类别进行分类（技术加固类、策略优化类、管理改进类、人员培训类），根据实施难度和周期进行分类（短期快速修复、中期系统加固、长期体系优化），使整改建议具有明确的优先级和可执行性。')
add_paragraph('（4）攻击思路防御建议：从攻击者视角出发，针对本次演练中采用的攻击思路和技术手法，提出对应的防御检测策略建议。包括但不限于：针对特定攻击技术的检测规则建议（SIEM关联规则、EDR检测策略、NTA流量特征等）、针对特定攻击链路的阻断策略建议（网络访问控制优化、应用层防护策略增强、主机加固策略等）、针对特定攻击场景的应急响应预案建议（钓鱼邮件应急流程、Webshell查杀流程、内网横向移动发现与处置流程等）。')
add_paragraph('（5）持续性改进方案：在整改建议基础上，提供安全建设的持续性改进路线图，帮助目标单位建立"以攻促防、以战练兵"的长效安全运营机制，将攻防演练的价值延续到日常安全运营中。')

# --- 1.2 信息收集方案 ---
add_heading_text('1.2 信息收集方案', level=3)

add_paragraph('信息收集是实网攻防演练的首要环节和基础工作，信息收集的全面性和准确性直接影响后续攻击阶段的效果。本方案根据招标文件要求，结合大型金融机构的实际特点，制定了系统化、多维度的信息收集方案，涵盖资产探测、信息收集、暴露面收集三大任务分项。')

add_paragraph('')
add_paragraph('1.2.1 资产探测方案', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('（1）域名资产探测', bold=True, first_line_indent=False)
add_paragraph('以目标单位主域名及其关联域名为起点，通过以下手段进行全面的子域名发现：')
add_paragraph('• DNS暴力枚举：基于行业常见子域名命名规范和字典，对目标域名的常见子域（如www、mail、vpn、oa、portal、admin、api、test、dev等）进行DNS解析查询。')
add_paragraph('• SSL证书透明度日志查询：利用Certificate Transparency（CT）日志数据库，检索包含目标域名及其关联域名的所有SSL/TLS证书信息，从中提取已颁发证书中包含的域名和子域名。')
add_paragraph('• 搜索引擎高级搜索：利用Google、Bing等搜索引擎的site语法，结合行业特定关键词，发现被搜索引擎收录的目标单位子域名。')
add_paragraph('• DNS区域传输检测：检测目标DNS服务器是否存在区域传输配置漏洞，若存在则获取完整的DNS区域记录。')
add_paragraph('• 关联域名发现：通过WHOIS查询、ICP备案信息查询、企业工商信息查询等渠道，获取目标单位的关联公司和分支机构域名信息。')

add_paragraph('')
add_paragraph('（2）IP资产探测', bold=True, first_line_indent=False)
add_paragraph('• IP段信息收集：通过WHOIS查询、BGP路由信息查询、AS号查询等手段，获取目标单位所属的IP地址段信息。')
add_paragraph('• IP存活扫描：对目标IP段进行全端口、全协议的存活扫描和端口扫描，识别活跃的IP地址及开放的服务端口。')
add_paragraph('• 服务识别与版本探测：对开放的端口进行服务类型和应用版本的深度识别，获取Web服务器、数据库、中间件、远程管理服务等的具体版本信息。')
add_paragraph('• 反向IP查询：通过DNS反向解析和CDN/云平台的反向IP查询，发现同一IP地址上托管的其他域名和应用。')

add_paragraph('')
add_paragraph('（3）应用资产探测', bold=True, first_line_indent=False)
add_paragraph('• Web应用识别：对所有发现的Web应用进行指纹识别，获取Web框架、CMS系统、开发语言、中间件版本等技术栈信息。')
add_paragraph('• 移动APP探测：对目标单位的手机银行APP、信用卡APP等移动应用进行信息收集，包括但不限于APP基本信息（包名、版本号）、APP反编译分析（提取API接口地址、硬编码密钥、第三方SDK信息等）、APP通信流量分析（抓包分析API通信协议和数据格式）。')
add_paragraph('• 小程序/公众号探测：通过微信、支付宝等平台的小程序搜索功能，发现目标单位及其关联方开发的小程序和公众号，分析其功能和API接口。')
add_paragraph('• API接口发现：通过对Web应用、移动APP、小程序的流量分析，识别和提取API接口端点，建立API接口清单。')

add_paragraph('')
add_paragraph('1.2.2 信息收集方案（社工信息）', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('（1）组织架构信息收集', bold=True, first_line_indent=False)
add_paragraph('• 通过目标单位官方网站的"关于我们"、"组织架构"、招聘信息等公开页面，收集组织架构信息。')
add_paragraph('• 通过企业工商信息查询平台，获取目标单位及其分支机构的工商注册信息、股东结构、高管名单等。')
add_paragraph('• 通过招聘网站（猎聘、BOSS直聘、拉勾等）的招聘信息，分析目标单位各业务线的人员配置和技术栈偏好。')

add_paragraph('')
add_paragraph('（2）员工信息收集', bold=True, first_line_indent=False)
add_paragraph('• 通过领英（LinkedIn）等职业社交平台，收集目标单位在职员工的职位、部门、工作经历、技能特长等信息，重点识别IT部门、安全部门、运维部门的员工。')
add_paragraph('• 通过技术社区（GitHub、Stack Overflow、CSDN、掘金等），搜索目标单位员工的技术活动记录，分析其使用的技术栈和可能暴露的内部信息。')
add_paragraph('• 通过社交媒体和论坛，收集员工的企业邮箱格式、命名规则等，为企业邮箱暴力破解或钓鱼攻击提供信息支持。')

add_paragraph('')
add_paragraph('（3）业务线信息收集', bold=True, first_line_indent=False)
add_paragraph('• 通过公开渠道（新闻稿、年报、行业报告等），收集目标单位的业务线分布、子公司/分支机构信息、供应链合作厂商信息等。')
add_paragraph('• 通过第三方合作平台和供应商招标公告，了解目标单位的IT供应商生态，分析可能的供应链攻击面。')

add_paragraph('')
add_paragraph('1.2.3 暴露面收集方案', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('（1）数据泄露检测', bold=True, first_line_indent=False)
add_paragraph('• 对暗网交易平台、黑客论坛、数据交易平台等渠道进行定向监测，检测目标单位相关的数据泄露事件。')
add_paragraph('• 对公开的数据库泄露合集进行检索，核实是否包含目标单位域名的邮箱账号和密码信息。')
add_paragraph('• 对历史安全事件和漏洞通报进行检索，了解目标单位曾经遭受的攻击和已公开的安全漏洞。')

add_paragraph('')
add_paragraph('（2）账号泄露检测', bold=True, first_line_indent=False)
add_paragraph('• 利用公开的账号泄露查询接口，对以目标单位域名为后缀的企业邮箱进行泄露检测。')
add_paragraph('• 对检测到的泄露账号信息进行整理分析，提取有效的账号密码组合，为后续的凭证猜解和登录尝试提供支持。')

add_paragraph('')
add_paragraph('（3）代码泄露检测', bold=True, first_line_indent=False)
add_paragraph('• 对GitHub、GitLab、Gitee、Bitbucket等代码托管平台进行关键词搜索，检测是否存在目标单位的源代码泄露，重点关注配置文件（含数据库连接串、API密钥、加密密钥等）、内部文档、运维脚本等。')
add_paragraph('• 对Pastebin、Gist等代码片段分享平台进行监控，检测是否存在目标单位相关的敏感信息泄露。')
add_paragraph('• 对云存储桶（AWS S3、阿里云OSS、腾讯云COS等）进行公开访问检测，检测是否存在目标单位相关的云存储配置不当导致的文件泄露。')

add_paragraph('')
add_paragraph('1.2.4 信息收集成果整理', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('信息收集阶段的所有成果将按照以下结构进行系统化整理和归档：')
add_paragraph('（1）资产清单：包含域名清单、IP地址清单、Web应用清单、移动APP清单、小程序/公众号清单、API接口清单等，每项资产标注发现方式、确认时间和关联信息。')
add_paragraph('（2）组织信息库：包含组织架构图、关键人员信息表、业务线分布信息等。')
add_paragraph('（3）泄露信息库：包含数据泄露记录、账号泄露记录、代码泄露记录、配置泄露记录等，标注泄露来源、泄露时间和风险等级。')
add_paragraph('（4）攻击面分析报告：基于以上信息，形成目标单位的互联网攻击面全景分析报告，标注高价值目标、高风险暴露面、潜在攻击入口等，为后续的线上攻防阶段提供明确的攻击方向和优先级。')

# --- 1.3 线上线下攻防方案 ---
add_heading_text('1.3 线上线下攻防方案', level=3)

add_paragraph('线上线下攻防是实网攻防演练的核心环节，分为线上攻防（互联网侧攻击）和线下攻防（内网侧攻击）两个阶段。本方案根据招标文件要求，结合金融行业的安全防护特点，制定了系统化、实战化的攻防方案。')

add_paragraph('')
add_paragraph('1.3.1 线上攻防方案（互联网侧攻击）', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('线上攻防阶段以突破互联网边界、获取内网初始访问权限为主要目标。根据招标文件要求，线上攻防涵盖漏洞扫描、漏洞利用、权限维持三大任务。')

add_paragraph('')
add_paragraph('（1）漏洞扫描方案', bold=True, first_line_indent=False)
add_paragraph('')
add_paragraph('A. Web应用漏洞扫描：')
add_paragraph('• 对信息收集阶段发现的所有Web应用资产进行全面漏洞扫描，覆盖OWASP Top 10常见Web安全风险，包括但不限于SQL注入、跨站脚本（XSS）、跨站请求伪造（CSRF）、服务端请求伪造（SSRF）、文件上传漏洞、文件包含漏洞、命令注入、不安全的反序列化、XXE注入等。')
add_paragraph('• 采用商用漏洞扫描器与自研定制化扫描脚本相结合的方式，提高漏洞发现的全面性和准确性。商用扫描器用于快速覆盖常见漏洞类型，自研定制化脚本用于针对性检测特定系统（如金融行业常见的网银系统、信贷系统、风控平台等）的特有漏洞模式。')
add_paragraph('• 对登录后的应用功能进行深度漏洞挖掘，针对前端表单校验绕过、业务逻辑漏洞（越权访问、参数篡改、流程绕过等）、API接口漏洞等进行专项检测。')

add_paragraph('')
add_paragraph('B. 系统服务漏洞扫描：')
add_paragraph('• 对开放端口的系统服务进行漏洞扫描，识别已知的CVE漏洞（如SSH、RDP、FTP、SMB、MySQL、Redis、MongoDB等服务的未授权访问和已知漏洞）。')
add_paragraph('• 重点关注弱口令和默认口令问题，对SSH、RDP、MySQL、Redis、Tomcat、WebLogic、JBoss等常见管理入口和服务进行弱口令检测。')
add_paragraph('• 对远程管理服务（如SSH、RDP、VNC、IPMI等）的配置安全性进行评估，检测是否存在允许空口令登录、允许root远程登录、未限制登录IP等不安全的配置。')

add_paragraph('')
add_paragraph('C. 中间件和框架漏洞扫描：')
add_paragraph('• 对Web中间件（如Apache、Nginx、IIS、Tomcat、WebLogic、JBoss、Jetty等）的版本进行已公开漏洞的匹配检测。')
add_paragraph('• 对开发框架（如Spring、Struts2、ThinkPHP、Laravel、Django、Fastjson、Shiro等）的版本进行已知高危漏洞的专项检测。')

add_paragraph('')
add_paragraph('（2）漏洞利用方案', bold=True, first_line_indent=False)
add_paragraph('')
add_paragraph('A. 漏洞验证与优先级排序：对扫描发现的漏洞进行手工验证，剔除误报，确认漏洞的真实性、可利用性和危害程度。按照漏洞危害程度（远程代码执行>任意文件读取>SQL注入>文件上传>SSRF>越权访问>信息泄露）和利用难度（直接利用>需要组合利用>需要特定条件）进行优先级排序，优先利用高危且易利用的漏洞。')

add_paragraph('')
add_paragraph('B. 漏洞利用策略：')
add_paragraph('• 远程代码执行漏洞利用：针对RCE类型漏洞，优先尝试获取Webshell或反弹Shell权限，建立对目标服务器的远程控制能力。')
add_paragraph('• SQL注入漏洞利用：尝试获取数据库数据（包括但不限于管理员账号密码、用户敏感信息、系统配置信息等），在条件允许的情况下尝试利用SQL Server的xp_cmdshell、MySQL的UDF提权等机制获取操作系统权限。')
add_paragraph('• 文件上传漏洞利用：尝试上传Webshell或其他可执行脚本，获取Web服务器权限。')
add_paragraph('• SSRF漏洞利用：尝试利用SSRF访问内网服务（如Redis、Memcached、Elasticsearch等），或结合其他漏洞（如Gopher协议利用）实现内网穿透。')
add_paragraph('• 未授权访问利用：针对Redis未授权访问、MongoDB未授权访问、Docker API未授权访问等，尝试直接获取数据或进一步获取服务器权限。')

add_paragraph('')
add_paragraph('C. 绕过与越权攻击：')
add_paragraph('• 认证绕过：尝试利用逻辑漏洞绕过登录认证，包括但不限于参数污染、响应篡改、JWT伪造、会话固定、条件竞争等。')
add_paragraph('• 权限越权：对已登录的应用功能进行水平越权（访问同权限级别的其他用户数据）和垂直越权（低权限用户访问高权限功能）测试。')
add_paragraph('• WAF/CDN绕过：对于部署了Web应用防火墙（WAF）或CDN防护的目标系统，采用协议层绕过、编码绕过、分块传输、HTTP参数污染等技术手段尝试绕过防护规则。')

add_paragraph('')
add_paragraph('（3）权限维持方案', bold=True, first_line_indent=False)
add_paragraph('')
add_paragraph('A. 痕迹清理：在成功获取服务器权限后，立即对攻击过程中的操作日志、命令历史、文件上传记录、进程记录等进行清理。清除Web服务器访问日志中与攻击行为相关的记录条目；清除系统命令历史（.bash_history、.zsh_history等）；删除或覆盖攻击过程中上传的工具文件和日志文件。')

add_paragraph('')
add_paragraph('B. 后门建立：')
add_paragraph('• Web层面：部署经过免杀处理的Webshell，采用加密通信、自定义参数、Referer验证、定时激活等机制增强隐蔽性。')
add_paragraph('• 系统层面：建立系统级的持久化后门，包括但不限于SSH authorized_keys植入、计划任务（crontab/at）、系统服务注册、内核模块加载、Rootkit安装等，具体方式根据目标系统的环境和防护能力灵活选择。')
add_paragraph('• 应用层面：在数据库、中间件、应用系统中植入后门账号或后门接口。')
add_paragraph('• 网络层面：建立SSH反向隧道、Socks5代理、VPN隧道等，确保在部分通信路径被封堵后仍有备用访问通道。')

add_paragraph('')
add_paragraph('C. 持久化保障：')
add_paragraph('• 多重备份：在目标环境中建立至少两种不同类型的后门机制，确保一种后门被清除后仍保有访问能力。')
add_paragraph('• 定时唤醒：配置后门定时执行健康检查和回联操作，确保在防火墙策略变化、服务重启等场景下后门仍能正常工作。')
add_paragraph('• 升级通道：建立后门的远程升级机制，能够根据后续攻击需要或环境变化对后门功能和通信方式进行动态调整。')

add_paragraph('')
add_paragraph('1.3.2 线下攻防方案（内网侧攻击）', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('线下攻防阶段以在目标内网环境中实现横向移动、获取核心网络区域访问权限为主要目标。根据招标文件要求，线下攻防涵盖资产扫描、权限维持、横向攻击三大任务。')

add_paragraph('')
add_paragraph('（1）内网资产扫描方案', bold=True, first_line_indent=False)
add_paragraph('')
add_paragraph('A. 内网拓扑探测：')
add_paragraph('• 网络拓扑发现：通过分析路由表、ARP表、DNS配置、DHCP配置等信息，绘制目标内网的网络拓扑结构。')
add_paragraph('• 网段探测：利用已获取的初始立足点，对可达的内网IP段进行存活探测和端口扫描，识别内网中的活跃主机和服务。')
add_paragraph('• VLAN和网络区域识别：通过分析IP地址分配、子网划分、ACL策略等信息，识别内网的VLAN划分和网络区域隔离情况。')

add_paragraph('')
add_paragraph('B. 关键资产识别：')
add_paragraph('• 域环境信息收集：识别域控制器、备份域控、DNS服务器、DHCP服务器等域基础设施的IP地址和主机名，获取域名称、域功能级别、域信任关系等信息。')
add_paragraph('• 集权系统识别：识别内网中的集中认证系统（AD域、LDAP、SSO单点登录、堡垒机、IAM等）、集中管理系统（SCCM、WSUS、Ansible、SaltStack等）、集中监控系统（Zabbix、Nagios、Prometheus等）。')
add_paragraph('• 核心业务系统识别：识别内网中的核心数据库（Oracle、MySQL、SQL Server、DB2等）、核心应用服务器、文件服务器、备份服务器等。')
add_paragraph('• 安全设备识别：识别内网中部署的安全设备（防火墙、IDS/IPS、WAF、EDR管理平台、SIEM平台等），了解安全监控的覆盖范围和检测手段。')

add_paragraph('')
add_paragraph('（2）权限维持与提升方案', bold=True, first_line_indent=False)
add_paragraph('')
add_paragraph('A. 凭证收集：')
add_paragraph('• 系统凭证提取：从已控制的主机中提取系统凭证信息，包括SAM数据库、LSASS进程内存中的明文密码和NTLM哈希、Kerberos TGT/ST票据、浏览器保存的密码、RDP/RDS连接凭证、WiFi密码等。')
add_paragraph('• 配置文件凭证提取：搜索文件系统中的配置文件、脚本文件、日志文件，提取其中包含的明文密码、连接串、API密钥、Token等敏感凭证信息。包括但不限于Web.config、application.properties、.env、docker-compose.yml、Ansible playbook、Shell脚本中的密码信息。')
add_paragraph('• 内存凭证提取：从运行进程的内存空间中提取敏感凭证信息（如从Java进程内存中提取JDBC连接串和密码、从Python进程内存中提取API密钥等）。')

add_paragraph('')
add_paragraph('B. 权限提升：')
add_paragraph('• Windows权限提升：利用Windows系统的本地提权漏洞（如内核漏洞、服务权限配置不当、计划任务权限配置不当、AlwaysInstallElevated注册表配置、UAC绕过等）将普通用户权限提升至SYSTEM权限。')
add_paragraph('• Linux权限提升：利用SUID二进制文件、Sudo配置不当、Cron任务权限配置不当、内核漏洞利用、Docker组权限滥用等途径将普通用户权限提升至root权限。')
add_paragraph('• 域权限提升：在获取域内普通用户凭证后，利用Kerberoasting攻击、AS-REP Roasting攻击、DCSync攻击、ACL滥用、组策略利用等手段提升到域管理员权限。')

add_paragraph('')
add_paragraph('（3）横向攻击方案', bold=True, first_line_indent=False)
add_paragraph('')
add_paragraph('A. 横向移动技术：')
add_paragraph('• Windows环境：利用WMI远程执行、PsExec远程执行、WinRM远程管理、计划任务远程创建、服务远程创建、DCOM远程调用、RDP远程桌面等方式在不同Windows主机之间进行横向移动。优先使用Windows内置的远程管理功能，减少对第三方工具的依赖。')
add_paragraph('• Linux环境：利用SSH密钥认证跳转、Ansible/Puppet/SaltStack等集中管理工具的远程执行能力、Redis/MongoDB等中间件的远程命令执行功能等方式在Linux主机之间进行横向移动。')
add_paragraph('• 跨平台：利用Web应用漏洞、数据库管理工具、中间件控制台等跨平台的管理入口实现在Windows和Linux环境之间的横向移动。')

add_paragraph('')
add_paragraph('B. 跨区域攻击策略：')
add_paragraph('• 网络边界突破：分析和利用不同网络区域之间的访问控制关系，寻找可被利用的跨区域访问路径（如DMZ区到内网的数据库连接、办公网到生产网的运维通道、测试环境到生产环境的同步通道等）。')
add_paragraph('• 双网卡主机利用：优先识别和控制同时连接多个网络区域的双网卡/多网卡主机（如跳板机、运维终端、监控服务器等），利用其作为跨区域访问的跳板。')
add_paragraph('• VPN和远程接入利用：分析和利用内网中的VPN设备和远程接入系统，获取对目标网络区域的远程访问能力。')

add_paragraph('')
add_paragraph('C. 定向社工攻击：')
add_paragraph('• 针对已获取的部分内部信息，在充分了解目标单位内部管理制度和业务流程的基础上，必要时采用定向社工方式攻击高价值目标。')
add_paragraph('• 利用已控制的内部邮箱账号，构造具有上下文关联的伪装邮件，提高社工攻击的成功率和隐蔽性。')
add_paragraph('• 社工攻击严格限制在可控范围内，确保不造成业务中断和数据泄露等负面影响。')

add_paragraph('')
add_paragraph('D. 核心目标攻克：')
add_paragraph('• 以核心网络区域（核心数据库区、核心业务系统区等）为最终攻击目标。')
add_paragraph('• 对域控制器进行重点突破，尝试获取域管理员权限以控制整个Windows域环境。')
add_paragraph('• 对核心数据库服务器进行重点突破，尝试获取数据库管理员权限及核心业务数据访问权限。')
add_paragraph('• 对运维管理平台（堡垒机、跳板机、ITSM平台等）进行重点突破，利用运维管理通道扩大攻击成果。')

# --- 1.4 成果汇报方案 ---
add_heading_text('1.4 成果汇报方案', level=3)

add_paragraph('成果汇报是攻防演练的最终环节，也是将攻击成果转化为安全防御价值的关键步骤。本方案根据招标文件要求，从成果总结、整改建议两个维度制定了系统化的成果汇报方案。')

add_paragraph('')
add_paragraph('1.4.1 成果总结方案', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('（1）攻击成果汇总', bold=True, first_line_indent=False)
add_paragraph('• 对线上线下攻防阶段取得的所有攻击成果进行全面梳理和汇总，按照攻击阶段（信息收集→初始入口→权限提升→横向移动→目标达成）进行系统化整理。')
add_paragraph('• 统计关键攻击指标：被攻破的互联网应用数量、获取的服务器权限数量、控制的内网主机数量、获取的域管理员/数据库管理员等高权限账号数量、突破的网络区域数量、触达的核心系统数量等。')
add_paragraph('• 按照目标系统类型进行分类汇总：Web应用系统、数据库系统、域控系统、运维管理系统、文件系统等。')

add_paragraph('')
add_paragraph('（2）攻击链路梳理', bold=True, first_line_indent=False)
add_paragraph('• 针对每条重要的攻击路径，梳理从初始信息收集到最终目标达成的完整攻击链路，形成清晰的攻击路径图。')
add_paragraph('• 攻击链路描述包括：每个攻击阶段使用的方法和技术、利用的漏洞和弱点、突破的安全防线、获取的权限和数据、攻击过程中遇到的主要障碍和克服方法。')
add_paragraph('• 对多条攻击路径进行综合分析，识别目标安全体系中的通用性薄弱环节和系统性风险。')

add_paragraph('')
add_paragraph('（3）重点成果专题说明', bold=True, first_line_indent=False)
add_paragraph('• 对具有代表性的重大攻击成果进行专题深度分析，还原攻击全过程，阐述攻击思路、技术手法和关键突破点。')
add_paragraph('• 对利用创新攻击手法或绕过高级安全防护取得的成果进行重点说明，展示攻击团队的实战能力和技术水平。')
add_paragraph('• 从防守方角度审视攻击成果，分析该成果所暴露的防御盲区和薄弱环节，引出后续的整改建议。')

add_paragraph('')
add_paragraph('（4）资产清单与漏洞清单交付', bold=True, first_line_indent=False)
add_paragraph('• 对信息收集和攻防过程中发现的所有互联网资产形成完整的资产清单，标注资产状态（活跃/不活跃）、端口开放情况、服务类型和版本信息等。')
add_paragraph('• 对攻防过程中发现和利用的所有安全漏洞形成完整的漏洞清单，包括漏洞名称、漏洞类型（OWASP分类）、影响资产、危害等级（严重/高危/中危/低危）、漏洞描述、复现步骤、修复建议等。每项漏洞标注CVE编号（如有）和CVSS评分。')
add_paragraph('• 资产清单和漏洞清单同时以Excel表格和PDF报告两种格式交付，方便不同场景的使用。')

add_paragraph('')
add_paragraph('1.4.2 整改建议方案', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('（1）技术修复建议', bold=True, first_line_indent=False)
add_paragraph('• 漏洞修复类：针对每个具体漏洞，提供详细的技术修复方案，包括补丁安装指引、配置修改方法、代码修改示例等。对于无法立即修复的漏洞（如业务系统短期内无法升级），提供缓解措施（如WAF虚拟补丁、访问控制策略调整、监控告警规则等）。')
add_paragraph('• 安全加固类：针对系统性安全问题，提供安全加固建议，包括但不限于操作系统安全基线加固、Web中间件安全配置优化、数据库安全配置优化、网络设备安全配置优化、应用系统安全架构优化等。')
add_paragraph('• 防护策略类：针对攻击者利用的攻击手法和技术路径，提供防护策略优化建议，包括但不限于WAF规则优化、IDS/IPS策略优化、EDR检测策略优化、SIEM关联规则优化、网络访问控制策略优化等。')

add_paragraph('')
add_paragraph('（2）管理改进建议', bold=True, first_line_indent=False)
add_paragraph('• 资产管理改进：针对攻击方发现的目标单位互联网资产管理盲区，建议建立完整的互联网资产台账和定期盘点机制，将"影子IT"纳入统一安全管理。')
add_paragraph('• 漏洞管理改进：针对已发现漏洞的修复周期过长、高危漏洞优先级不明确等管理问题，建议优化漏洞管理流程，建立基于风险的漏洞修复SLA机制。')
add_paragraph('• 权限管理改进：针对权限过大、特权账号管理不规范等管理问题，建议实施最小权限原则和特权账号管理（PAM）机制。')

add_paragraph('')
add_paragraph('（3）人员培训建议', bold=True, first_line_indent=False)
add_paragraph('• 安全意识培训：针对社工攻击利用的员工安全意识薄弱环节，建议开展全员网络安全意识培训，重点覆盖钓鱼邮件识别、社交工程防范、密码安全管理等内容。')
add_paragraph('• 安全技术培训：针对安全运维人员在攻击事件发现和响应方面的能力短板，建议开展安全技术专项培训，覆盖日志分析、威胁狩猎、应急响应等内容。')

add_paragraph('')
add_paragraph('1.4.3 成果汇报交付物', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('根据招标文件要求，本包件交付物为《攻防演练成果报告》，具体内容包括：')
add_paragraph('（1）攻防演练总体情况概述')
add_paragraph('（2）信息收集阶段成果详情')
add_paragraph('（3）线上攻防阶段成果详情（含攻击链路图）')
add_paragraph('（4）线下攻防阶段成果详情（含攻击链路图）')
add_paragraph('（5）重点攻击成果专题分析')
add_paragraph('（6）资产清单与漏洞清单')
add_paragraph('（7）整改建议（技术修复、管理改进、人员培训三个维度）')
add_paragraph('（8）防守策略建议（针对攻击思路的检测与防御建议）')
add_paragraph('（9）攻防演练工作总结与展望')

doc.add_page_break()

# ================================================================
# 2. 质量承诺及保证体系、措施
# ================================================================
doc.add_heading('2. 质量承诺及保证体系、措施', level=2)

add_paragraph('我公司高度重视本项目的服务质量，承诺为本项目建立完善的质量管理体系，确保各项服务工作按照招标文件要求高标准完成。')

add_paragraph('')
add_heading_text('2.1 质量承诺', level=3)

add_paragraph('')
add_paragraph('（1）我公司郑重承诺：严格按照招标文件规定的服务内容、服务要求、技术标准和服务周期开展各项工作，确保服务成果全面满足招标人要求，服务质量达到行业领先水平。')
add_paragraph('（2）承诺为本项目投入经验丰富的专业技术团队，团队人员均具备网络安全攻防领域的深厚技术积累和丰富的金融行业项目实施经验，确保服务团队的技术能力和项目经验与项目需求相匹配。')
add_paragraph('（3）承诺在项目实施过程中严格遵守国家法律法规、行业标准和招标人的各项管理制度，确保项目实施的合规性和规范性。')
add_paragraph('（4）承诺对服务过程中发现的所有安全漏洞和风险隐患进行真实、完整、准确的记录和报告，不隐瞒、不虚报、不篡改。')
add_paragraph('（5）承诺提供的各项服务不存在任何权利瑕疵和质量瑕疵，服务成果的知识产权归属清晰，不侵犯任何第三方的合法权益。')
add_paragraph('（6）承诺不以任何形式将本项目转包或违法分包给其他单位，确保项目团队人员与投标文件承诺的人员一致。')

add_paragraph('')
add_heading_text('2.2 质量管理体系', level=3)

add_paragraph('')
add_paragraph('我公司将为本项目建立三级质量管理体系，确保服务质量的全程可控。')

add_paragraph('')
add_paragraph('（1）项目级质量管理', bold=True, first_line_indent=False)
add_paragraph('• 项目经理作为项目质量的第一责任人，对项目整体质量负责。')
add_paragraph('• 建立项目质量计划，明确各阶段的质量目标、质量标准、质量控制点和质量检查方法。')
add_paragraph('• 项目启动阶段进行质量策划，明确质量要求并传达至每位团队成员。')
add_paragraph('• 项目实施过程中进行质量跟踪，定期检查各项工作的完成质量。')

add_paragraph('')
add_paragraph('（2）公司级质量管理', bold=True, first_line_indent=False)
add_paragraph('• 公司质量管理部门对项目进行不定期的质量审计和抽查。')
add_paragraph('• 对项目关键节点（信息收集阶段完成、线上攻防阶段完成、线下攻防阶段完成、成果报告交付）进行里程碑质量评审。')
add_paragraph('• 建立客户满意度调查机制，定期向招标人收集服务满意度反馈。')

add_paragraph('')
add_paragraph('（3）人员能力保障', bold=True, first_line_indent=False)
add_paragraph('• 建立团队人员能力评估机制，在项目启动前对团队成员的技术能力、项目经验进行复核确认。')
add_paragraph('• 项目实施过程中定期组织技术交流和经验分享，持续提升团队整体能力水平。')
add_paragraph('• 针对项目中遇到的复杂技术问题，及时调动公司级专家资源提供技术支持。')

add_paragraph('')
add_heading_text('2.3 质量保证措施', level=3)

add_paragraph('')
add_paragraph('（1）服务过程质量控制', bold=True, first_line_indent=False)
add_paragraph('• 信息收集阶段：建立信息收集质量检查清单，确保资产探测覆盖全面、信息收集维度完整、暴露面检测无遗漏。信息收集成果需经项目经理审核确认后方可进入下一阶段。')
add_paragraph('• 攻防实施阶段：建立攻击操作日志和成果记录机制，每日汇总攻击进展和发现成果，确保攻击过程的规范性和成果的可追溯性。对高危漏洞利用和敏感操作进行双人复核，确保攻击行为的可控性。')
add_paragraph('• 成果汇报阶段：建立成果报告多级审核机制，报告经项目经理初审、技术负责人复审、公司质量管理部门终审后方可提交招标人。')

add_paragraph('')
add_paragraph('（2）文档质量管理', bold=True, first_line_indent=False)
add_paragraph('• 所有交付文档遵循统一的格式规范和命名规则。')
add_paragraph('• 技术报告要求结构清晰、内容完整、数据准确、建议可行。')
add_paragraph('• 报告中的技术术语使用规范，攻击链路描述清晰，整改建议具体可落地。')

add_paragraph('')
add_paragraph('（3）问题管理与持续改进', bold=True, first_line_indent=False)
add_paragraph('• 建立项目问题跟踪机制，对服务过程中发现的任何质量问题进行记录、分析和整改。')
add_paragraph('• 建立经验教训总结机制，在项目各阶段结束后进行回顾总结，持续优化改进服务质量。')
add_paragraph('• 建立客户反馈快速响应机制，对招标人提出的任何质量意见或建议，在24小时内给予响应和反馈。')

add_paragraph('')
add_paragraph('（4）服务确认与签收', bold=True, first_line_indent=False)
add_paragraph('• 每次服务均需招标人业务部门进行签收确认，确保服务内容的完整性和满意度。')
add_paragraph('• 服务过程中定期向招标人汇报工作进展和阶段性成果，确保信息的透明和对称。')
add_paragraph('• 服务结束前，配合招标人完成全面的服务验收，确保所有交付成果均符合招标文件要求。')

doc.add_page_break()

# ================================================================
# 3. 安全保密措施、保密管理制度、保密协议承诺及模板
# ================================================================
doc.add_heading('3. 安全保密措施、保密管理制度、保密协议承诺及模板', level=2)

add_heading_text('3.1 安全保密措施', level=3)

add_paragraph('我公司充分认识到本项目涉及公安部第三研究所的重要信息资产和网络安全敏感信息，将安全保密工作置于项目管理的首要位置。针对本项目的特殊性，制定以下全方位的安全保密措施：')

add_paragraph('')
add_paragraph('（1）组织保障措施', bold=True, first_line_indent=False)
add_paragraph('• 成立项目保密工作小组，由项目经理担任保密工作负责人，全面负责项目的保密管理工作。')
add_paragraph('• 在项目启动阶段，组织全体项目成员进行保密教育培训，明确保密义务和违规责任。')
add_paragraph('• 项目团队所有成员在进入项目工作前，必须签署《保密承诺书》，承诺对项目过程中接触到的所有信息严格保密。')

add_paragraph('')
add_paragraph('（2）数据安全管理措施', bold=True, first_line_indent=False)
add_paragraph('• 项目实施过程中产生的所有数据（包括但不限于资产信息、漏洞信息、攻击记录、系统截图、账号密码、网络拓扑等）均视为敏感数据，实施严格的访问控制和权限管理。')
add_paragraph('• 根据信息资料的最小接触原则，确定不同角色人员的接触范围和知悉程度。项目成员根据各自的任务分工，仅接触和利用与其工作直接相关的数据资料，不接触超出其职责范围的信息。')
add_paragraph('• 所有项目数据存储在加密的专用设备中，严禁存储在个人设备或公共云存储中。')
add_paragraph('• 项目数据的传输使用加密通道（如加密邮件、加密即时通信、VPN等），严禁通过不安全的渠道传输项目敏感数据。')

add_paragraph('')
add_paragraph('（3）技术保密措施', bold=True, first_line_indent=False)
add_paragraph('• 攻击工具和脚本实现专人专用、定期更新，工具使用完毕后及时销毁或回收。')
add_paragraph('• 攻击过程中获取的目标系统权限、凭证、数据等，仅限项目授权人员在规定的时间范围内使用，严禁超范围、超时限使用。')
add_paragraph('• 渗透测试过程全程记录操作日志，确保所有操作行为可追溯、可审计。')

add_paragraph('')
add_paragraph('（4）物理安全措施', bold=True, first_line_indent=False)
add_paragraph('• 项目资料文件载体（纸质文档、U盘、移动硬盘等）的制作、保管、交付采取必要的保密手段。')
add_paragraph('• 纸质项目文档使用专用的保密文件柜存放，使用时在指定保密区域进行。')
add_paragraph('• 电子存储介质（U盘、移动硬盘等）进行全盘加密，使用完毕后按照涉密介质销毁规程进行安全销毁。')

add_paragraph('')
add_paragraph('（5）项目结束后保密措施', bold=True, first_line_indent=False)
add_paragraph('• 项目结束后，所有项目相关的电子数据在招标人确认后进行安全清除（使用符合国家保密标准的数据擦除方法）。')
add_paragraph('• 项目相关的纸质文档在招标人确认后进行安全销毁（使用粉碎机或专业销毁服务）。')
add_paragraph('• 项目团队成员在项目结束后的保密义务不随项目结束而终止，需持续对项目过程中接触的敏感信息承担保密责任。')

add_paragraph('')
add_heading_text('3.2 保密管理制度', level=3)

add_paragraph('我公司已建立完善的保密管理制度体系，为本项目的保密管理提供制度保障。以下为本公司保密管理制度的主要内容（具体证明材料另附并加盖公章）：')

add_paragraph('')
add_paragraph('第一章 总则', bold=True, first_line_indent=False)
add_paragraph('第一条 为加强本公司信息安全保密管理工作，保护客户信息资产安全，防止敏感信息泄露，根据《中华人民共和国保守国家秘密法》《中华人民共和国网络安全法》《中华人民共和国数据安全法》等相关法律法规，结合本公司实际情况，制定本制度。')
add_paragraph('第二条 本制度适用于本公司全体员工，包括但不限于正式员工、试用期员工、实习生、外聘顾问、外包人员等，以及所有参与公司项目的第三方人员。')
add_paragraph('第三条 保密工作实行"积极防范、突出重点、依法管理"的方针，遵循"谁主管、谁负责"、"业务谁开展、保密谁负责"的原则。')

add_paragraph('')
add_paragraph('第二章 保密范围和密级管理', bold=True, first_line_indent=False)
add_paragraph('第四条 保密范围包括但不限于：客户的技术信息、业务数据、系统架构、网络拓扑、安全漏洞、攻击记录、员工信息、商业秘密以及其他在项目实施过程中获知的未公开信息。')
add_paragraph('第五条 根据信息敏感程度，将保密信息分为三级：绝密级（造成特别严重损害）、机密级（造成严重损害）、秘密级（造成损害）。本项目中客户的所有信息系统信息和攻防演练数据均按机密级及以上标准进行管理。')

add_paragraph('')
add_paragraph('第三章 保密管理职责', bold=True, first_line_indent=False)
add_paragraph('第六条 公司设立保密工作领导小组，由公司主要负责人担任组长，全面负责公司的保密管理工作。')
add_paragraph('第七条 项目经理为本项目的保密工作第一责任人，负责项目保密措施的制定、落实和监督检查。')
add_paragraph('第八条 全体员工对本岗位的保密工作承担直接责任，应当自觉遵守保密制度，履行保密义务。')

add_paragraph('')
add_paragraph('第四章 涉密人员管理', bold=True, first_line_indent=False)
add_paragraph('第九条 涉密人员上岗前须经过保密审查，签署保密承诺书，接受保密教育培训。')
add_paragraph('第十条 涉密人员在岗期间须定期接受保密教育和监督检查。')
add_paragraph('第十一条 涉密人员离岗离职时，须交清所有涉密载体，签订离岗保密承诺书，承诺继续履行保密义务。')

add_paragraph('')
add_paragraph('第五章 涉密载体管理', bold=True, first_line_indent=False)
add_paragraph('第十二条 涉密载体的制作、收发、传递、使用、复制、保存、维修和销毁，须符合国家保密规定和公司保密管理要求。')
add_paragraph('第十三条 涉密电子数据须存储在加密设备中，严禁在连接互联网的计算机上处理涉密信息。')
add_paragraph('第十四条 涉密载体的传递须通过安全可靠的渠道进行，严禁通过普通快递、公共网络等方式传递。')

add_paragraph('')
add_paragraph('第六章 保密监督检查', bold=True, first_line_indent=False)
add_paragraph('第十五条 公司保密管理部门定期对各部门和项目的保密工作进行检查，发现问题及时督促整改。')
add_paragraph('第十六条 对违反保密制度的行为，视情节轻重给予警告、罚款、解除劳动合同等处分；构成犯罪的，依法移送司法机关处理。')

add_paragraph('')
add_paragraph('第七章 附则', bold=True, first_line_indent=False)
add_paragraph('第十七条 本制度由公司保密工作领导小组负责解释和修订。')
add_paragraph('第十八条 本制度自发布之日起施行。')

add_paragraph('')
add_heading_text('3.3 保密协议承诺及模板', level=3)

add_paragraph('')
add_paragraph('保密协议承诺函', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, font_size=14, first_line_indent=False)
add_paragraph('')
add_paragraph('我公司郑重承诺：在项目启动前，将与本项目的所有团队成员（包括项目经理、高级人员、中级人员、初级人员及其他可能接触项目信息的辅助人员）逐一签订保密协议，确保每一位成员明确保密义务和法律责任。保密协议的签订将作为项目人员上岗的前提条件，未签署保密协议的人员不得参与项目任何工作。以下为我公司为本项目团队人员准备的保密协议模板：')
add_paragraph('')

add_paragraph('保密协议', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, font_size=14, first_line_indent=False)
add_paragraph('')
add_paragraph('甲方（用人单位）：________________________')
add_paragraph('乙方（员工）：________________________')
add_paragraph('')
add_paragraph('鉴于乙方在甲方工作期间，将接触和知悉甲方客户的商业秘密、技术秘密和其他未公开信息（以下统称"保密信息"），为明确乙方的保密义务，保护甲方客户的合法权益，根据《中华人民共和国保守国家秘密法》《中华人民共和国劳动合同法》《中华人民共和国反不正当竞争法》等相关法律法规，甲乙双方经平等协商，达成如下协议：')
add_paragraph('')
add_paragraph('第一条 保密信息范围', bold=True, first_line_indent=False)
add_paragraph('本协议所指的保密信息包括但不限于：')
add_paragraph('（1）客户的技术信息：包括但不限于信息系统架构、网络拓扑结构、安全防护策略、系统配置信息、源代码、数据库结构、安全漏洞信息、渗透测试结果、攻击记录、修复方案等。')
add_paragraph('（2）客户的业务信息：包括但不限于业务流程、业务数据、用户信息、交易记录、财务报表、战略规划、内部管理制度等。')
add_paragraph('（3）客户的人员信息：包括但不限于员工姓名、联系方式、组织架构、岗位职责等。')
add_paragraph('（4）项目过程信息：包括但不限于项目方案、工作记录、会议纪要、阶段性报告、最终交付成果等。')
add_paragraph('（5）其他甲方明确告知需要保密的信息，或乙方应当知道需要保密的信息。')
add_paragraph('')
add_paragraph('第二条 保密义务', bold=True, first_line_indent=False)
add_paragraph('乙方承诺并同意：')
add_paragraph('（1）在服务期间及服务结束后，不以任何形式泄露、复制、传播或利用客户的保密信息。')
add_paragraph('（2）不将保密信息用于本项目之外的任何其他用途。')
add_paragraph('（3）不向任何第三方（包括但不限于其他客户、竞争对手、媒体、社交平台等）提供或披露保密信息。')
add_paragraph('（4）仅在完成本职工作所必需的最小范围内接触和使用保密信息。')
add_paragraph('（5）发现保密信息已经或可能泄露时，立即向甲方和客户报告，并积极配合采取补救措施。')
add_paragraph('（6）保密义务不因劳动合同的终止、解除或本项目的结束而终止，保密义务持续有效。')
add_paragraph('')
add_paragraph('第三条 保密信息载体的管理', bold=True, first_line_indent=False)
add_paragraph('（1）乙方不得私自复制、摘录、拍照、截屏或以其他方式留存保密信息。')
add_paragraph('（2）乙方不得将含有保密信息的设备、U盘、移动硬盘、纸质文档等载体带离工作场所（经甲方书面批准的除外）。')
add_paragraph('（3）工作关系终止时，乙方应将所有含有保密信息的载体（包括个人设备中存储的相关信息）交还甲方，不得私自留存。')
add_paragraph('')
add_paragraph('第四条 违约责任', bold=True, first_line_indent=False)
add_paragraph('（1）乙方违反本协议任何条款的，甲方有权立即终止乙方的项目参与资格，并保留追究其法律责任的权利。')
add_paragraph('（2）因乙方违反保密义务给甲方或客户造成损失的，乙方应承担全部赔偿责任。')
add_paragraph('（3）乙方违反保密义务的行为涉嫌犯罪的，甲方将依法移送司法机关处理。')
add_paragraph('')
add_paragraph('第五条 其他条款', bold=True, first_line_indent=False)
add_paragraph('（1）本协议自双方签字（或盖章）之日起生效。')
add_paragraph('（2）本协议一式两份，甲乙双方各执一份，具有同等法律效力。')
add_paragraph('（3）本协议的签订、履行、解释及争议解决均适用中华人民共和国法律。')
add_paragraph('')
add_paragraph('甲方（盖章）：________________       乙方（签字）：________________')
add_paragraph('日期：        年      月      日       日期：        年      月      日')

doc.add_page_break()

# ================================================================
# 4. 应急响应能力
# ================================================================
doc.add_heading('4. 应急响应能力', level=2)

add_heading_text('4.1 应急响应方案', level=3)

add_paragraph('在实网攻防演练过程中，可能出现各类突发情况，包括但不限于：攻击行为意外导致目标系统异常、误操作影响业务系统正常运行、发现重大安全隐患需要紧急通报、目标单位发生真实安全攻击事件等。我公司建立完善的应急响应机制，确保在各类突发情况下能够快速、有序、有效地进行应对。')

add_paragraph('')
add_paragraph('（1）应急响应组织体系', bold=True, first_line_indent=False)
add_paragraph('• 建立项目应急响应指挥体系，由项目经理担任应急总指挥，负责应急响应的统一指挥和协调调度。')
add_paragraph('• 项目团队全体成员均为应急响应成员，根据各自的专业特长分工负责不同类型的应急事件。')
add_paragraph('• 建立与招标人安全管理部门的应急联络机制，确保应急情况下信息沟通的畅通和高效。')

add_paragraph('')
add_paragraph('（2）应急响应分级', bold=True, first_line_indent=False)
add_paragraph('根据突发事件的严重程度和影响范围，将应急事件分为三个等级：')
add_paragraph('• 一级（严重）：攻击行为已造成或在可预见的时间内可能造成业务系统中断、数据丢失或严重损坏的情况；发现可能导致重大安全事故的严重安全漏洞。')
add_paragraph('• 二级（一般）：攻击行为导致目标系统出现暂时性性能下降、个别服务短暂不可用等情况，可在短时间内恢复正常；发现中高危安全漏洞。')
add_paragraph('• 三级（轻微）：攻击行为未对目标系统造成可感知的影响，仅涉及低风险操作；发现低危安全漏洞或一般性安全隐患。')

add_paragraph('')
add_paragraph('（3）应急响应流程', bold=True, first_line_indent=False)
add_paragraph('')
add_paragraph('A. 事件发现与报告：')
add_paragraph('• 项目团队任何成员发现或预见到可能发生的应急事件，应在第一时间（不超过5分钟）向项目经理报告。')
add_paragraph('• 项目经理接到报告后，迅速进行初步评估，确定事件等级，并向招标人指定联络人报告。')
add_paragraph('• 对于一级应急事件，应立即（不超过5分钟）报告招标人并启动应急响应；对于二级应急事件，应在15分钟内报告并启动响应；对于三级应急事件，应在30分钟内报告并采取相应措施。')

add_paragraph('')
add_paragraph('B. 应急处置：')
add_paragraph('• 立即停止当前可能导致问题加剧的攻击行为。')
add_paragraph('• 对事件影响范围和原因进行快速调查分析。')
add_paragraph('• 根据事件类型和等级，采取相应的应急处置措施（详见各类型应急预案）。')
add_paragraph('• 在应急处理过程中，保持与招标人的实时沟通，及时汇报处置进展。')

add_paragraph('')
add_paragraph('C. 事件恢复与复盘：')
add_paragraph('• 确认事件影响已完全消除，相关系统恢复正常状态。')
add_paragraph('• 对事件进行详细记录，包括事件时间线、影响范围、处置措施、恢复结果等。')
add_paragraph('• 组织事件复盘会议，分析事件根因，总结应急处置经验教训，优化应急预案。')

add_paragraph('')
add_paragraph('（4）各类型应急预案', bold=True, first_line_indent=False)
add_paragraph('')
add_paragraph('A. 攻击引发目标系统异常应急预案：')
add_paragraph('• 立即暂停所有对目标系统的攻击操作。')
add_paragraph('• 记录异常发生前的最后一次攻击操作内容、时间和目标。')
add_paragraph('• 协助招标人技术团队对异常原因进行排查分析。')
add_paragraph('• 在确认攻击操作与系统异常的因果关系后，调整攻击策略和技术手段，避免同类问题再次发生。')
add_paragraph('• 在招标人确认系统恢复正常且同意继续攻击后，恢复攻击活动。')

add_paragraph('')
add_paragraph('B. 发现重大安全漏洞应急预案：')
add_paragraph('• 立即记录漏洞详细信息（漏洞名称、影响范围、危害等级、复现步骤）。')
add_paragraph('• 第一时间通过安全通信渠道向招标人指定联络人通报漏洞信息，不通过任何其他渠道传播。')
add_paragraph('• 配合招标人技术团队进行漏洞影响评估和紧急修复。')
add_paragraph('• 在漏洞修复完成前，暂停对该漏洞的进一步利用操作。')
add_paragraph('• 漏洞修复完成后，协助招标人进行修复验证，确认漏洞已被有效修复。')

add_paragraph('')
add_paragraph('C. 误操作应急预案：')
add_paragraph('• 立即停止当前操作，评估误操作的影响范围和严重程度。')
add_paragraph('• 如误操作可能对目标系统造成损害，立即向招标人报告。')
add_paragraph('• 积极配合招标人技术团队采取恢复措施（如数据恢复、配置还原等）。')
add_paragraph('• 详细记录误操作经过和处置过程，纳入事后复盘。')

add_paragraph('')
add_paragraph('D. 信息泄露应急响应预案：')
add_paragraph('• 一旦发现或怀疑保密信息发生泄露或存在泄露风险，立即向项目经理和招标人报告。')
add_paragraph('• 评估泄露信息的类型、数量、影响范围。')
add_paragraph('• 在招标人指导下，采取应急处置措施，包括但不限于：通知相关部门和人员、启动舆情监控、联系相关平台删除泄露内容等。')
add_paragraph('• 配合招标人进行事件调查，确定泄露原因和泄露渠道。')
add_paragraph('• 根据调查结果，采取补救措施和追责问责。')

add_paragraph('')
add_heading_text('4.2 应急响应时间承诺', level=3)

add_paragraph('')
add_paragraph('应急响应时间承诺书', bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, font_size=14, first_line_indent=False)
add_paragraph('')
add_paragraph('我公司就本项目的应急响应时间作出以下郑重承诺：')
add_paragraph('')
add_paragraph('1. 项目服务期间，提供7×24小时应急响应服务。项目团队保持24小时通讯畅通，确保在任何时间（含节假日）均可接收应急通知并启动应急响应。')
add_paragraph('2. 从接到应急通知到开始应急响应处置的时间承诺≤2小时（含远程响应和现场响应）。如情况需要现场处置，承诺在2小时内到达招标人指定的上海市服务地点。')
add_paragraph('3. 应急事件现场处置期间，项目团队持续驻场工作，直至应急事件得到有效控制和解决。')
add_paragraph('4. 应急响应团队核心成员（项目经理及至少一名高级技术人员）在应急响应启动后30分钟内建立应急通信群组，确保信息传递的及时性和准确性。')
add_paragraph('5. 应急事件处置完毕后，在24小时内提交书面的应急事件处置报告，包括事件概述、时间线、处置措施、恢复结果和改进建议。')
add_paragraph('6. 对于因我方操作引发的应急事件，我方承担由此产生的全部责任和损失。')
add_paragraph('')
add_paragraph('以上承诺为我公司对本项目应急响应能力的正式承诺，如有违反，愿承担相应的法律和合同责任。')
add_paragraph('')

add_table_with_style(
    ['序号', '如遇突发情况最快应急响应时间'],
    [['1', '≤2小时']]
)

add_paragraph('')
add_paragraph('投标人授权代表签字：________________')
add_paragraph('（加盖企业公章）')
add_paragraph('日   期：________________')

add_paragraph('')
add_heading_text('4.3 应急响应团队名单及联系方式', level=3)

add_paragraph('')
add_paragraph('我公司为本项目专门组建应急响应团队，以下为应急响应团队名单及联系方式：')
add_paragraph('')

add_table_with_style(
    ['序号', '岗位', '姓名', '身份证', '联系方式'],
    [
        ['1', '应急总指挥（项目经理）', '', '', ''],
        ['2', '应急技术负责人（高级人员）', '', '', ''],
        ['3', '应急技术工程师（中级人员）', '', '', ''],
        ['4', '应急值班人员（初级人员）', '', '', ''],
        ['5', '应急值班人员（初级人员）', '', '', ''],
    ]
)

add_paragraph('注：以上人员姓名、身份证号及联系方式将在项目启动后正式填写并提供给招标人。')
add_paragraph('')
add_paragraph('投标人授权代表签字：________________')
add_paragraph('（加盖企业公章）')
add_paragraph('日   期：________________')

doc.add_page_break()

# ================================================================
# TECHNICAL SECTION - PERSONNEL PLAN (人员配备方案)
# ================================================================
add_heading_text('附录：人员配备方案', level=2)
add_paragraph('（本部分作为技术方案的补充，同时满足商务部分附件7和附件8的要求）', first_line_indent=False)

add_heading_text('一、服务人员配置方案', level=3)

add_paragraph('根据招标文件包件一人员要求（项目组须配备高级人员至少1人，中级人员至少1人，初级人员至少2人），我公司为本项目配置以下专业技术服务团队：')

add_paragraph('')
add_paragraph('（一）团队组织架构', bold=True, first_line_indent=False)
add_paragraph('本项目团队采用"1+1+2+N"的人员配置模式，即1名项目经理（高级人员）、1名高级攻防工程师（中级人员）、2名攻防工程师（初级人员），并根据项目阶段性需要灵活调配后端技术支持专家资源（N），确保项目各阶段的人力资源配置满足实际工作需要。')

add_paragraph('')
add_paragraph('（二）团队角色与职责', bold=True, first_line_indent=False)

add_paragraph('')
add_paragraph('1. 项目经理（高级人员，1名）', bold=True, first_line_indent=False)
add_paragraph('• 职责：全面负责本项目的管理工作，包括项目策划、进度管理、质量管理、风险管理、沟通协调、团队管理等。作为与招标人的主要联络人，负责项目全过程的沟通汇报和需求响应。')
add_paragraph('• 资质要求：至少6年以上网络安全领域工作经验，具有丰富的金融行业安全项目经验，主导过多项大型攻防演练或渗透测试项目的实施工作。持有CISP、CISAW或网络与信息安全管理员等相关资质证书。')
add_paragraph('• 项目经历：具有多项与本项目类似的金融行业安全风险评估和攻防演练项目实施经验。')

add_paragraph('')
add_paragraph('2. 高级攻防工程师（中级人员，1名）', bold=True, first_line_indent=False)
add_paragraph('• 职责：负责攻防演练核心技术的实施，包括信息收集阶段的资产探测和漏洞扫描、线上线下攻防阶段的攻击实施、成果汇报阶段的技术分析等。作为项目的主要技术执行者，对攻击的质量和深度负责。')
add_paragraph('• 资质要求：至少4年以上网络安全领域工作经验，具有金融行业安全项目经验，参与过多项渗透测试或攻防演练项目的实施工作。持有CISP、CISAW或网络与信息安全管理员等相关资质证书。')
add_paragraph('• 技术能力：熟练掌握Web安全、内网渗透、域渗透、社会工程学等多种攻击技术，具有丰富的实战经验。')

add_paragraph('')
add_paragraph('3. 攻防工程师（初级人员，2名）', bold=True, first_line_indent=False)
add_paragraph('• 职责：在项目经理和高级攻防工程师的指导下，参与信息收集、漏洞扫描、攻击实施、成果整理等各环节的具体执行工作。负责项目过程中的文档记录、数据整理和报告撰写支撑。')
add_paragraph('• 资质要求：至少2年以上安全领域工作经验，具有安全风险评估项目经验，参与过多项安全项目的实施工作。')
add_paragraph('• 技术能力：具备Web安全基础知识，熟悉常见安全漏洞的原理和利用方法，具备基本的渗透测试能力。')

add_paragraph('')
add_paragraph('4. 后端技术支持专家（N名，按需投入）', bold=True, first_line_indent=False)
add_paragraph('• 在项目关键阶段（如重大漏洞利用、域控突破、核心系统攻坚等），根据实际需要及时调动公司后端技术支持专家资源，为项目实施提供强力的技术支撑和攻坚保障。后端技术支持专家不占用项目组常驻人员编制，根据项目需要灵活调配。')

add_paragraph('')
add_paragraph('（三）人员稳定性保障措施', bold=True, first_line_indent=False)
add_paragraph('• 项目启动时，明确各团队成员在本项目中的工作职责和工作量，确保团队人员能够全职投入本项目工作。')
add_paragraph('• 为项目团队核心成员配置备选人员，建立AB角机制，确保在突发情况下（如人员离职、生病等）能够及时补充，不影响项目正常推进。')
add_paragraph('• 建立团队人员激励机制和项目专项奖励，提升团队人员对项目的归属感和工作积极性。')
add_paragraph('• 如需更换人员，提前向招标人提交书面申请并说明原因，以保证项目平稳进行。新更换人员将具有与原人员同等或更高的资质、经验和技术水平，并获得招标人书面同意后方可进行更换。如因人员更换影响项目服务工作的，由我方承担所有损失责任。')

add_paragraph('')
add_paragraph('（四）人员稳定性承诺', bold=True, first_line_indent=False)
add_paragraph('')
add_paragraph('我公司郑重承诺：保持本项目服务人员的稳定性。除非招标人书面同意，不更换已投入本项目的服务人员。如需更换，将以同等或更高条件的人员取代需更换的人员。若因人员更换影响本服务工作，由我方承担所有损失责任。')
add_paragraph('')
add_paragraph('（本承诺可单独出具承诺书并加盖公章）', first_line_indent=False)

doc.add_page_break()

# ================================================================
# SAVE
# ================================================================
output_path = '/Users/jun/售前_长亭/售前_长亭/01_项目跟进/06_杨智超/02_交行攻防演练/投标文件_包件1_完整版.docx'
doc.save(output_path)
print(f'Document saved to: {output_path}')
print('Done!')
