DATA = {
    'printline': {
        'title': '1. Hàm in chữ (printline)',
        'content': '''+-----------------------------------------------------------------------------+
| 1. Hàm in chữ (printline)                                                   |
+-----------------------------------------------------------------------------+

Hàm này in một dòng chữ lên màn hình tại vị trí dòng chỉ định. Sau khi gọi, bạn phải dùng render.ddd4 để cập nhật màn hình mới thấy kết quả.
(Có nhiều loại hàm in chữ nhưng tôi sẽ chỉ nhắc đến printline vì nó là cơ bản nhất)

Địa chỉ: 23DC8

Tham số:
  - R0: linepos (khoảng cách từ pixel đầu của chữ tới đỉnh màn hình. 1->31)
  - R1: pad (giá trị không ảnh hưởng, thường để 30 cho đủ 2 byte)
  - ER2: địa chỉ của chuỗi ký tự

Cách gọi:
```asm
xr0 = 0x<pad><linepos> , <địa chỉ của chuỗi kí tự>
printline
render.ddd4
```

Ví dụ: in "Xin chào" ở dòng 3 (linepos = 21)
```asm
org 0xe9e0 # địa chỉ của program
setup: # đây là label , bạn đặt tên tuỳ ý
    buffer_clear # xoá sạch màn hình
    setlr        # giúp program không bị treo khi sử dụng hàm có BL hoặc rt (trong program này không cần thiết)
    setsfr       # giúp khởi tạo màn hình và bàn phím (program này không cần)
    setlr_pc     # kết hợp giữa setlr và nhảy (program này không cần)
inchu:
    xr0 = 0x3021 , adr_of text    # pad = 30, linepos = 21 ; adr_of nghĩa là địa chỉ của label
    printline                     # in chữ
    render.ddd4                   # cập nhật màn hình
text:
    str "Xin~chào"    # text
    0x00              # cần có để kết thúc chữ
```

Giải thích:
  - ta có:
    + r0 là 21 (linepos) , r1 là 30 (pad)
    + ghép lại thành: hex 21 30
    + tức 0x3021 (nhắc lại 0x sẽ ngược lại với hex)
  - adr_of text là địa chỉ của nhãn text, nơi chứa chuỗi.
  - render.ddd4 bắt buộc phải có để hiển thị.
  - lùi đầu dòng trong program chỉ để cho dễ nhìn, trên thực tế ta có thể cách, có thể không và cách bao nhiêu tuỳ thích

Lưu ý về linepos:
  + Dòng 1: 01
  + Dòng 2: 11
  + Dòng 3: 21
  + Dòng 4: 31
  (Đây là các linepos thường dùng)

Lưu ý về in chữ:
  - với printline là in chữ font to (0E) nên tối đa chỉ in được 17 chữ'''
    },

    'smallprint': {
        'title': '2. Hàm in chữ font (smallprint)',
        'content': '''+-----------------------------------------------------------------------------+
| 2. Hàm in chữ font (smallprint)                                             |
+-----------------------------------------------------------------------------+

Hàm này in một dòng chữ với kích thước font nhỏ (8x8 pixel) tại vị trí dòng chỉ định.

Địa chỉ: 23DCC

Tham số:
  - r0: kích thước font ( là 08, 0a, 0e)
  - r1: linepos (vị trí dòng từ 01 -> 31)
  - er2: địa chỉ của chuỗi ký tự

Cách gọi:
```asm
xr0 = 0x<linepos><font> , <địa chỉ của text>
smallprint
render.ddd4
```

Ví dụ: in "Xin chào" bằng font to ở dòng 2 và chữ "Hello" font vừa ở dòng 3
```asm
org 0xe9e0
start:
    setlr
    setsfr
    buffer_clear
inchu:
    xr0 = 0x110e , adr_of text1
    smallprint
    xr0 = 0x210a , adr_of text2
    smallprint

    render.ddd4     # lưu ý ở đây chỉ cần render.ddd4 một lần
text1:
    str "~~Xin~chào"
    0x00
text2:
    str "~~Hello"
    0x00
```

Giải thích:
  - smallprint in chữ với font bé 08, mỗi dòng có thể chứa nhiều ký tự hơn printline.
  - render.ddd4 vẫn bắt buộc phải gọi sau khi in.

Lưu ý:
  - Kích thước font thường là 08 (nhỏ), 0a (trung bình), 0e (to)
  - linepos từ 01 đến 31
  - chỉ font to mới có thể dùng kí tự tiếng việt'''
    },

    'render_bitmap': {
        'title': '3. Hàm vẽ bitmap (render_bitmap)',
        'content': '''+-----------------------------------------------------------------------------+
| 3. Hàm vẽ bitmap (render_bitmap)                                            |
+-----------------------------------------------------------------------------+

Hàm này vẽ một hình ảnh bitmap lên màn hình tại tọa độ và kích thước chỉ định.
Dữ liệu bitmap là các bit pixel, mỗi byte đại diện cho 8 pixel theo chiều ngang.

Địa chỉ: 09848

Tham số:
  - xr0: hex <x_pos> <y_pos> <width> <height>   (mỗi giá trị 1 byte, phải chuyển từ Dec sang Hex)
  - er0: adr_of bitmap

Cách gọi:
```asm
xr0 = hex <x_pos> <y_pos> <width> <height>
render_bitmap
er0 = adr_of bitmap
render.ddd4
```

Ví dụ: vẽ hình vuông 8x8 tại (10,10)
```asm
org 0xe9e0
start:
    buffer_clear
    setlr
    setsfr
ve:
    xr0 = hex 0A 0A 08 08      # x=10 (0x0A), y=10, rộng=8, cao=8
    render_bitmap
    er0 = adr_of hinh
    render.ddd4
hinh:
    hex ff 81 81 81 81 81 81 ff   # 8x8 ô vuông viền
```

Giải thích:
  - xr0 = hex 0A 0A 08 08 : x=10 (0x0A), y=10 (0x0A), width=8 (0x08), height=8 (0x08)
  - render_bitmap vẽ vào bộ đệm hiện tại, render.ddd4 cập nhật màn hình

Lưu ý:
  - Các số như 10, 8 phải chuyển sang hex: 10 -> 0A, 8 -> 08.
  - Bitmap phải vừa đúng kích thước (width * height / 8 byte)
  - Nếu vượt ra ngoài màn hình, hàm sẽ không vẽ.'''
    },

    'line_draw': {
        'title': '4. Hàm vẽ đường thẳng (line_draw)',
        'content': '''+-----------------------------------------------------------------------------+
| 4. Hàm vẽ đường thẳng (line_draw)                                           |
+-----------------------------------------------------------------------------+

Hàm này vẽ một đường thẳng từ điểm (x1, y1) đến điểm (x2, y2).

Địa chỉ: 08E62

Tham số:
  - xr0: hex <x1> <y1> <x2> <y2>   (mỗi giá trị 1 byte, phải chuyển từ số sang hex)

Cách gọi:
```asm
xr0 = hex <x1> <y1> <x2> <y2>
line_draw
render.ddd4
```

Ví dụ: vẽ đường chéo từ (0,0) đến (192,63)
```asm
org 0xe9e0
start:
    buffer_clear
    setlr
    setsfr
ve:
    xr0 = hex 00 00 c0 3f        # x1=0, y1=0, x2=192 (0xC0), y2=63 (0x3F)
    line_draw
    render.ddd4
# không cần dữ liệu thêm
```

Giải thích:
  - xr0 = hex 00 00 c0 3f : (0,0) đến (192,63)
  - line_draw vẽ đường thẳng vào bộ đệm, render.ddd4 cập nhật màn hình

Lưu ý:
  - Các số phải chuyển sang hex: 192 -> C0, 63 -> 3F.
  - Tọa độ x từ 0 đến 191, y từ 0 đến 63 (màn hình 192x64 pixel).
  - render.ddd4 bắt buộc phải gọi sau khi vẽ.'''
    },

    'waitshift': {
        'title': '5. Hàm chờ phím SHIFT (waitshift)',
        'content': '''+-----------------------------------------------------------------------------+
| 5. Hàm chờ phím SHIFT (waitshift)                                          |
+-----------------------------------------------------------------------------+

Hàm này tạm dừng chương trình và chờ người dùng nhấn phím SHIFT.
Khi SHIFT được nhấn, chương trình tiếp tục chạy.

Địa chỉ: 23DDE

Cách gọi:
```asm
waitshift
```

Ví dụ: in "Đã nhấn SHIFT" sau khi nhấn SHIFT
```asm
org 0xe9e0
start:
    buffer_clear
    setlr
    setsfr
print:
    waitshift                     # chờ nhấn SHIFT
    xr0 = 0x3021 , adr_of text
    printline
    render.ddd4
text:
    str "Da~nhan~SHIFT"
```

Giải thích:
  - waitshift sẽ đứng yên cho đến khi SHIFT được nhấn.
  - Sau đó chương trình in dòng chữ "Da nhan SHIFT" ở dòng 3.

Lưu ý:
  - Không cần tham số, không cần render trước waitshift.
  - Nên đặt waitshift sau các khởi tạo cơ bản.'''
    },

    'calc_func': {
        'title': '6. Hàm tính toán (calc_func)',
        'content': '''+-----------------------------------------------------------------------------+
| 6. Hàm tính toán (calc_func)                                                 |
+-----------------------------------------------------------------------------+

Hàm này thực hiện một phép tính được cho dưới dạng token (mã hex) và trả về kết quả dưới dạng số NUM (10 byte). Rất hữu ích để tính toán các biểu thức phức tạp.

Địa chỉ: 17922

Tham số:
  - xr0: hex <addr_calc_ptr> <addr_result>
    + addr_calc_ptr: địa chỉ của một vùng nhớ chứa địa chỉ thực của phép tính.
    + addr_result: địa chỉ vùng nhớ để lưu kết quả (10 byte).

Cách gọi:
```asm
xr0 = hex <addr_calc_ptr> <addr_result>
calc_func
```

Ví dụ: tính 36+67
```asm
tinh:
    xr0 = adr_of addr_calc_ptr , adr_of result
    calc_func
# vùng nhớ chứa con trỏ đến phép tính
addr_calc_ptr:
    adr_of calc                     # địa chỉ thực của phép tính
# vùng nhớ chứa phép tính (token)
calc:
    hex 33 36 a6 36 37 00         # "36+67", 00 ở cuối là bắt buộc
# vùng nhớ chứa kết quả (10 byte)
result:
    hex 00 00 00 00 00 00 00 00 00 00
```

Giải thích:
  - calc_func đọc token, tính toán, ghi kết quả dạng NUM vào result

Lưu ý:
  - Kết quả trả về là dạng NUM (10 byte), không phải số hex thông thường.'''
    },

    'cmp_ea': {
        'title': '7. Hàm so sánh bảng (cmp_ea) (quan trọng)',
        'content': '''+-----------------------------------------------------------------------------+
| 7. Hàm so sánh bảng (cmp_ea)                                                  |
+-----------------------------------------------------------------------------+

Hàm cmp_ea (09C20) so sánh giá trị trong ER0 với các mục trong bảng được trỏ bởi EA.
Mỗi mục gồm 2 byte giá trị so sánh, sau đó là 2 byte dữ liệu. Khi tìm thấy mục có giá trị bằng ER0, EA sẽ được cập nhật để trỏ đến dữ liệu ngay sau giá trị đó. Nếu không tìm thấy, EA sẽ trỏ đến dữ liệu của mục cuối.

Cơ chế:
  - EA ban đầu trỏ đến đầu bảng.
  - Hàm duyệt từng mục, so sánh 2 byte đầu của mỗi mục với ER0.
  - Nếu khớp, EA sẽ trỏ đến 2 byte tiếp theo (dữ liệu), kết thúc.
  - Nếu không khớp, EA nhảy đến mục tiếp theo (cách 4 byte).
  - Nếu gặp 00 00 thì dừng, lúc này EA trỏ đến giá trị sau 00 00.

Sau khi cmp_ea, ta có thể dùng các gadget để lấy dữ liệu từ EA:
  - 1C64A: ER6 = [EA]  (đọc 2 byte)
  - 1C2C0: QR0 = [EA], LEA D002H, [EA] = QR0  (đọc 8 byte, tăng EA, ghi lại – thường dùng để lấy 2 byte đầu)

Ví dụ: so sánh ER0 với 0x3667, nếu bằng thì lấy 0x1234, nếu không thì lấy 0x0000.
```asm
cmp:
    er0 = 0x3667
    ea = adr_of table
    cmp_ea
    qr0 = [ea], lea D002H, [ea] = qr0   # đọc 8 byte vào QR0, lúc này QR0 chứa dữ liệu
table:
    0x3667
    0x1234
    0x0000
    0x5678
```

Giải thích:
  - Nếu ER0 == 0x3667, cmp_ea sẽ đặt EA trỏ đến 0x1234 (2 byte sau 0x3667).
  - Lệnh qr0 = [ea] đọc 8 byte bắt đầu từ 0x1234. Nếu vùng nhớ đó chỉ có 2 byte dữ liệu (0x1234) và các byte sau không quan trọng, QR0 sẽ có 0x1234 ở 2 byte đầu.
  - Nếu ER0 không bằng 0x3667, cmp_ea sẽ gặp mục 0x0000 và đặt EA trỏ đến 0x5678.
  - qr0 = [ea] đọc 8 byte từ địa chỉ ea đang trỏ vào (là 56 78 ...) nên QR0 = hex 56 78 ...
  - LEA D002H, [ea] = qr0 là thao tác phụ (đặt EA = D002, đặt giá trị tại EA = QR0 tức là D002 = QR0), không ảnh hưởng kết quả.

Lưu ý:
  - Có thể dùng gadget 1C64A (ER6 = [EA]) nếu chỉ cần lấy 2 byte dữ liệu.
  - Dữ liệu trong bảng không nhất thiết phải là địa chỉ, có thể là giá trị số, mã lệnh,...
  - Các bảng thường kết thúc bằng 0x0000 là trường hợp mặc định (giống default trong switch-case của C)'''
    },

    'getkey': {
        'title': '8. Các hàm đọc phím (getkey, getscancode)',
        'content': '''+-----------------------------------------------------------------------------+
| 8. Các hàm đọc phím (getkey, getscancode, getscancode_nodelay)             |
+-----------------------------------------------------------------------------+
Có ba hàm đọc phím thường dùng trong ROP, phân biệt bởi hành vi chờ và độ trễ.

8.1. getkey / getscancode_nodelay (không chờ)

Hàm này đọc phím và trả vào địa chỉ trong ER0. Nếu không có phím bấm thì không thay đổi giá trị.
Lý do không xảy ra hiện tượng "kẹt phím" có thể được suy ra từ phần 4.1.1.
Keycode KI/KO (2 byte) được ghi vào địa chỉ chỉ định.

Địa chỉ: 2F5EA

Tham số:
  - er0: địa chỉ để lưu keycode

Cách gọi:
```asm
er0 = adr_of key
getkey # hoặc cũng có thể dùng getscancode_nodelay
key:
    hex 00 00
```

8.2. getscancode (chờ)

Hàm này đọc phím và dừng chương trình cho đến khi có phím được bấm.

Địa chỉ: 1F24E

Tham số:
  - er0: địa chỉ để lưu keycode

Cách gọi:
```asm
er0 = adr_of key
getscancode
# kiểm tra key có khác 0 không
key:
    hex 00 00
```

Lưu ý chung:
  - Keycode thu được là KI/KO (2 byte)

8.3. Bảng keycode (KI/KO)

Dưới đây là bảng keycode KI/KO của các phím trên Casio fx-580VN X.
Mỗi phím có giá trị 2 byte (KI, KO). Dùng để so sánh với kết quả từ getkey/getscancode.
```asm
hex 80 01   # [SHIFT]
hex 80 02   # [ALPHA]
hex 40 04   # [←]
hex 80 08   # [→]
hex 80 04   # [↑]
hex 40 08   # [↓]
hex 80 10   # [MENU]
hex 40 01   # [OTPN]
hex 40 02   # [CALC]
hex 40 10   # [TÍCH PHÂN]
hex 40 02   # [X]
hex 20 01   # [PHÂN SỐ]
hex 20 02   # [√]
hex 20 04   # [x²]
hex 20 08   # [xˆ]
hex 20 10   # [log]
hex 20 20   # [IN]
hex 10 01   # [(-)]
hex 10 02   # [ĐỘ]
hex 10 04   # [x^-1]
hex 10 08   # [SIN]
hex 10 10   # [COS]
hex 10 20   # [TAN]
hex 08 01   # [STO]
hex 08 02   # [ENG]
hex 08 04   # [(]
hex 08 08   # [)]
hex 08 10   # [S<=>D]
hex 08 20   # [M+]
hex 04 10   # [AC]
hex 02 10   # [÷]
hex 01 10   # [-]
hex 04 40   # [x10]
hex 01 40   # [=]
hex 10 40   # [0]
hex 01 01   # [1]
hex 01 02   # [2]
hex 01 04   # [3]
hex 02 01   # [4]
hex 02 02   # [5]
hex 02 04   # [6]
hex 04 01   # [7]
hex 04 02   # [8]
hex 04 04   # [9]
hex 04 08   # [DEL]
hex 02 08   # [×]
hex 01 08   # [+]
hex 08 40   # [.]
hex 02 40   # [ANS]
```

Để sử dụng hiệu quả hàm này, cần kết hợp với hàm cmp_ea'''
    },

    'delay': {
        'title': '9. Hàm làm chậm (delay)',
        'content': '''+-----------------------------------------------------------------------------+
| 9. Hàm làm chậm (delay)                                                     |
+-----------------------------------------------------------------------------+

Hàm này tạm dừng chương trình trong một khoảng thời gian nhất định.
Thời gian trễ phụ thuộc vào giá trị truyền vào er0.

Địa chỉ: 09F3C

Tham số:
  - er0: giá trị thời gian trễ (2 byte)

Cách gọi:
```asm
er0 = hex 0x<giá trị>
delay
```

Ví dụ: in chữ "LỌ" delay 1 giây tức 8000 tick (0x1f40) rồi in chữ "THÁNH" đè lên chữ "LỌ"
```asm
org 0xe9e0
start:
    buffer_clear
    setlr
    setsfr

print:
    xr0 = 0x3011 , adr_of text1
    printline
    render.ddd4

    er0 = 0x1f40
    delay

    xr0 = 0x3011 , adr_of text2
    printline
    render.ddd4

text1:
    str "LỌ"
    0x00
text2:
    str "THÁNH"
    0x00
```

Giải thích:
  - er0 = 0x1f40 (1 giây). Giá trị càng lớn, thời gian trễ càng lâu.
  - Hàm delay sẽ dừng chương trình trong khoảng thời gian tương ứng, sau đó tiếp tục chạy.

Lưu ý:
  - Delay thường dùng để tạo hiệu ứng chậm hoặc đồng bộ thời gian.'''
    },

    'verify': {
        'title': '10. Các dạng so sánh (verify)',
        'content': '''+-----------------------------------------------------------------------------+
| 10. Các dạng so sánh (verify)                                               |
+-----------------------------------------------------------------------------+
Trong các phần mềm, đôi khi ta không chỉ muốn so sánh bằng mà còn muốn so sánh các điều kiện khác. Khi ấy ta sử dụng các hàm có sẵn từ chế độ verify của máy.

Các hàm verify:
```
- 19536 : verify_eq   (==)
- 195C0 : verify_ne   (!=)
- 19516 : verify_gt   (>)
- 19526 : verify_lt   (<)
- 194F6 : verify_ge   (>=)
- 19506 : verify_le   (<=)
```

Các hàm này lần lượt kiểm tra giữa 2 giá trị: bằng nhau, khác nhau, lớn hơn, bé hơn, không bé hơn (lớn hơn hoặc bằng), không lớn hơn (bé hơn hoặc bằng).

Cách gọi:
```asm
xr0 = <địa chỉ 1>, <địa chỉ 2>
call <verify function>
```

Ví dụ:
```asm
value_a:
    0x0001
value_b:
    0x0001
xr0 = adr_of value_a , adr_of value_b
call 19536 # verify_eq kiểm tra value_a có bằng value_b
```

Kết quả: trả về: er0 = 00 01 và er2 = 01 00 (True), còn nếu value_b là giá trị khác thì sai (False) er0 = er2 = 00 00.

Để sử dụng hiệu quả ta nên dùng kết hợp với cmp_ea'''
    },

    'loop': {
        'title': '11. Kỹ thuật xây dựng vòng lặp (loop)',
        'content': '''+-----------------------------------------------------------------------------+
| 11. Kỹ thuật xây dựng vòng lặp (loop)                                       |
+-----------------------------------------------------------------------------+

Trong ROP, "loop" không phải là một lệnh có sẵn, mà là kỹ thuật để chương trình chạy lại từ đầu sau khi hoàn thành một lượt. Nếu không có loop, khi chạy hết chương trình sẽ bị treo.

Có hai dạng loop phổ biến: loop (dùng QR0 và strcpy) và loop ngắn (dùng memcpy_auto_jmp). Cả hai đều sao chép chương trình từ vùng backup về vùng chạy rồi nhảy về đầu, tạo vòng lặp vô hạn.

11.1. Loop – dùng QR0 và strcpy (phổ biến)

Mẫu loop:
```asm
loop:
    qr0 = 0xd62e3030d184d630
    call 0x203c8
    sp = er6, pop er8
```

Giải thích từng bước:
 1. qr0 = 0xd62e3030d184d630
    - QR0 là thanh ghi 8 byte. 4 byte thấp (XR0) = 0xD184D630, 4 byte cao (XR4) = 0xD62E3030.
    - Kết quả: er0 = 0xD630, er2 = 0xD184.
 2. call 0x203c8
    - Gọi hàm strcpy (hoặc memcpy). Tham số: er0 = đích (0xD630), er2 = nguồn (0xD184).
    - Sao chép toàn bộ dữ liệu từ 0xD184 đến 0xD630, dừng khi gặp 0x00.
 3. sp = er6, pop er8  (gadget 0x21F74)
    - Gadget này thực hiện:
        mov sp, er6        (SP = er6)
        pop er8            (lấy 2 byte từ SP vào er8, SP tăng 2)
        pop pc             (lấy 2 byte tiếp theo vào PC, SP tăng 2)
    - Ở đây er6 phải được thiết lập trước đó, thường là 0xD62E (0xD630 - 2). Khi đó:
        SP = 0xD62E
        pop er8 → lấy 2 byte rác (0x3030) vào er8, SP = 0xD630
        pop pc → lấy 2 byte đầu tiên tại 0xD630 vào PC, đó là lệnh đầu tiên của chương trình vừa được sao chép. Chương trình bắt đầu chạy lại.

Tóm lại: loop ngắn sao chép chương trình từ 0xD184 → 0xD630, rồi nhảy vào 0xD630. Cách này ngắn gọn, tiết kiệm byte, phù hợp khi chương trình nhỏ.

11.2. Loop ngắn – dùng memcpy_auto_jmp

Mẫu loop:
```asm
loop:
    call 0x2045c     # pop xr4, pop xr12
    0xd730           # địa chỉ đích (dest)
    0x01fe           # độ dài chương trình (len)
    0xe9e0           # địa chỉ nguồn (src)
    0xd724           # src - 0xC (địa chỉ trả về)
    call 0x2b2ba     # memcpy_auto_jmp
```

Giải thích từng bước:
 1. call 0x2045c
    - Gadget "pop xr4, pop xr12". Lấy 8 byte từ stack vào xr4 (4 byte) và xr12 (4 byte).
    - Các tham số được đặt ngay sau lệnh call, theo thứ tự: dest, len, src, return_addr.
 2. Các tham số:
    - 0xd730 : địa chỉ đích (dest). Được nạp vào er4.
    - 0x01fe : độ dài chương trình (len). Được nạp vào er6 (khoảng 510 bytes).
    - 0xe9e0 : địa chỉ nguồn (src). Được nạp vào er12.
    - 0xd724 : địa chỉ trả về (src - 0xC). Được nạp vào er14.
 3. call 0x2b2ba (memcpy_auto_jmp)
    - Hàm thực hiện memcpy với các tham số:
        er4 = dest (0xD730)
        er6 = len  (0x01FE)
        er12 = src  (0xE9E0)
        er14 = return_addr - 0xC (0xD724)
    - Sao chép một khối dữ liệu từ src đến dest với độ dài len.
    - Sau khi sao chép, nó tự động nhảy đến địa chỉ trong er10 (0xD724) để tiếp tục. Đây là cơ chế "auto_jmp", giúp không cần thêm gadget pivot riêng.

Tóm lại: loop dài sao chép chương trình từ vùng backup 0xE9E0 (nơi lưu bản sao an toàn) về vùng chạy 0xD730, sau đó nhảy đến 0xD724. Cách này phù hợp khi cần copy toàn bộ chương trình với độ dài xác định, không phụ thuộc vào byte null.

Lưu ý chung cho cả hai dạng:
  - Vùng backup là 0xE9E0 (cách 0xD730 + 4784 byte), nơi lưu bản sao an toàn.

Q: Vì sao lại -0xC trong loop ngắn?
A: Xét disas của memcpy_auto_jmp, ta thấy sau khi cpy xong nó thực hiện B LEAVE tức là vào hàm LEAVE (0AC38). Mà hàm LEAVE đặt sp = er14 (nên từ đầu cho return addr = er14 là như vậy), pop xr4, pop qr8, nên tổng số byte SP tăng là 4 + 8 = 12 (bytes). Vì thế phải -12 để bù vào.

LUÔN DÙNG org 0xd730 THAY VÌ org 0xe9e0 KHI CÓ LOOP TRONG PROGRAM'''
    },

    'offset': {
        'title': '12. Offset – Cách tính địa chỉ chính xác',
        'content': '''+-----------------------------------------------------------------------------+
| 12. Offset – Cách tính địa chỉ chính xác                                     |
+-----------------------------------------------------------------------------+

Trong ROP, khi viết chương trình, bạn thường xuyên phải truy cập vào các ô nhớ cụ thể, đặc biệt là các biến trong vùng backup (0xE9E0). Khái niệm offset giúp bạn xác định chính xác vị trí cần truy cập.

Offset là khoảng cách (tính bằng byte) từ một địa chỉ cơ sở đến địa chỉ bạn muốn. Trong tài liệu này, ta hay dùng cách viết như adr_of [+4784] để chỉ địa chỉ backup. Bản chất của nó là phép cộng: địa chỉ backup = địa chỉ runtime + 4784.

Để hiểu rõ hơn, hãy xét một ví dụ với gadget pop er0:

pop er0    # địa chỉ 0x12602, mã hex: 02 26 31 30

```asm
pop er0    # tương đương với hex: 02 26 31 30
```

Bốn byte này (02 26 31 30) được đặt vào vùng nhớ của chương trình. Nếu bạn muốn lưu dữ liệu ngay sau gadget (ví dụ giá trị 36 67), bạn có thể viết:

```asm
pop er0        # hex: 02 26 31 30
hex 36 67      # dữ liệu nằm ngay sau 4 byte của lệnh call
```

Lúc này, trong bộ nhớ runtime (0xD730), các byte được sắp xếp như sau:
```
Địa chỉ 0xD730 : 02 26 31 30 36 67 ...
```

- Nếu bạn trỏ đến địa chỉ 0xD730 (offset +0), đó là byte đầu tiên của lệnh call.
- Nếu bạn trỏ đến 0xD734 (offset +4), đó là dữ liệu 36 67.
- Nếu bạn trỏ đến 0xD730 + 4784 (tức 0xE9E0), đó là bản sao của chính 4 byte trên, nhưng nằm ở vùng backup. Lúc này offset +4784 giúp bạn truy cập vào bản sao.

Tại sao phải dùng offset +4784?

Như đã giải thích trong phần loop, vùng runtime (0xD730) bị ghi đè mỗi lần chương trình lặp lại. Muốn thay đổi dữ liệu có hiệu lực lâu dài, bạn phải thay đổi chính bản sao trong vùng backup (0xE9E0). Do đó, khi bạn viết:

```asm
er8 = adr_of [+4784] bien
```

thì er8 sẽ chứa địa chỉ của bien trong vùng backup, không phải runtime.

Vì sao lại là 4784?

Con số 4784 xuất phát từ khoảng cách giữa địa chỉ runtime 0xD730 và địa chỉ backup 0xE9E0. Cụ thể: 0xE9E0 - 0xD730 = 0x12B0 = 4784 (thập phân). Vùng backup này được chọn vì nó nằm ngoài vùng bị ghi đè bởi cơ chế loop (0xD184 → 0xD630), do đó các dữ liệu được lưu tại đây sẽ không bị mất sau mỗi lần lặp. Đây là lý do vì sao ta cần dùng offset +4784 khi muốn thay đổi lâu dài.

Quy tắc xác định offset:
  - adr_of chỉ một label (ví dụ bien) sẽ cho địa chỉ runtime (0xD730 + khoảng cách từ đầu program).
  - adr_of [+4784] bien sẽ cho địa chỉ runtime + 4784, tức là địa chỉ của biến đó trong vùng backup.
  - Trong các gadget có pop er8 hoặc pop pc, địa chỉ nhảy thường phải trừ đi 2 (hoặc 4, 8) để bù cho các pop phía trước. Đó cũng là một dạng offset.

Tóm lại:
  - Offset là khoảng cách byte giữa các địa chỉ.
  - +4784 là offset chuẩn để chuyển từ vùng runtime sang vùng backup.
  - Khi bạn muốn thay đổi giá trị có tính lâu dài, hãy dùng offset +4784.'''
    },

    'incdec': {
        'title': '13. Tăng/Giảm giá trị của một địa chỉ',
        'content': '''+-----------------------------------------------------------------------------+
| 13. Tăng/Giảm giá trị của một địa chỉ                                        |
+-----------------------------------------------------------------------------+

Một thao tác rất phổ biến trong ROP là tăng/giảm giá trị tại một địa chỉ.

Gadget sử dụng: [er8] += er2, pop xr8, rt
  địa chỉ: 09CA0

Cách dùng:
```asm
er8 = địa chỉ cần thay đổi (2 byte)
er2 = giá trị cần cộng (2 byte, có thể âm dạng bù hai)
[er8] += er2, pop xr8, rt
0x30303030          # pad cho pop xr8
```

Giá trị thường dùng:
```
hex 00 01   : tăng 1
hex ff ff   : giảm 1 (vì 0xFFFF = -1)
```

Ví dụ: tăng giá trị tại 0xE9E0 lên 1
```asm
er8 = 0xE9E0
er2 = 0x0001
[er8] += er2, pop xr8, rt
0x30303030
```

Giải thích:
  - Sau [er8] += er2, pop xr8, rt, bộ nhớ tại 0xE9E0 sẽ được cộng thêm 1.
  - Gadget có pop xr8 ở cuối, nên cần 4 byte pad (0x30303030) để tránh ảnh hưởng đến stack. Giá trị pad không quan trọng, miễn là có. Nhưng đôi khi nên tận dụng nó.

Lưu ý:
  - Nếu muốn giảm, dùng er2 = 0xFFFF.
  - Có thể dùng giá trị khác để tăng với số lớn hơn.
  - Để ghi vào vùng backup (lâu dài), dùng địa chỉ có offset +4784.
    + Ví dụ: er8 = adr_of [+4784] gay

Scroll – Cuộn màn hình liên tục

Địa chỉ 0xF039 trong bộ nhớ điều khiển độ cuộn (scroll) của màn hình. Thay đổi giá trị tại đây sẽ làm màn hình cuộn lên/xuống.

Để tạo hiệu ứng cuộn liên tục, ta kết hợp:
  - Kỹ thuật tăng/giảm tại địa chỉ
  - Hàm delay để điều chỉnh tốc độ.
  - Vòng lặp (loop) để lặp lại.

Mẫu code cuộn lên (tăng giá trị):
```asm
scroll_up:
    er8 = 0xF039
    er2 = 0x0001
    [er8]+=er2,pop xr8
    0x30303030            # pad
    er0 = 0x0500
    delay                 # delay
loop:
    [...]
```

Mẫu code cuộn xuống (giảm giá trị):
```asm
scroll_down:
    er8 = 0xF039
    er2 = 0xFFFF
    [er8]+=er2,pop xr8
    0x30303030
    er0 = 0x0500
    delay
loop:
    [...]
```

Giải thích:
  - Mỗi bước tăng/giảm 1 đơn vị tại 0xF039, làm màn hình cuộn một lượng nhỏ.
  - Delay giữa các bước để cuộn chậm vừa phải (có thể điều chỉnh giá trị).
  - loop để tăng/giảm liên tục tạo hiệu ứng cuộn.

Lưu ý:
  - Giá trị tại 0xF039 không nên tăng/giảm quá nhanh (cần delay) để tránh nổ.
  - Nếu cuộn đến giới hạn, giá trị có thể bị tràn.'''
    },

    'set': {
        'title': '14. Ghi giá trị vào một địa chỉ (set)',
        'content': '''+-----------------------------------------------------------------------------+
| 14. Ghi giá trị vào một địa chỉ (set)                                        |
+-----------------------------------------------------------------------------+

Để ghi dữ liệu vào một ô nhớ, ta dùng gadget [er0] = r2 (208B2) hoặc [er0] = er2 (139D8).

Cách dùng với xr0 (ghi 2 byte):
```asm
xr0 = <địa chỉ đích> , <giá trị> , <pad>
[er0] = r2
```

Giải thích:
  - xr0 gồm er0 (2 byte thấp) và er2 (2 byte cao).
  - Khi viết xr0 = addr, value, pad, ta thực chất đang đặt:
      er0 = addr
      r2 = value (byte thấp của er2, vì pad chiếm byte cao)
  - Sau đó gadget [er0] = r2 sẽ ghi 1 byte value vào addr.
  - Pad (thường là 30) không ảnh hưởng, chỉ để đủ 4 byte cho xr0.

Ví dụ: ghi giá trị 0x41 vào địa chỉ 0xE9E0
```asm
xr0 = 0xE9E0 , 0x41 , 0x30
[er0] = r2
```

Nếu cần ghi 2 byte, dùng gadget [er0] = er2 (139D8) và xr0 = addr, value_high, value_low:
```asm
xr0 = 0xE9E0 , 0x12 , 0x34
[er0] = er2      # ghi 0x3412 vào 0xE9E0 (little‑endian)
```

Lưu ý:
  - Để ghi vào vùng backup (lâu dài), dùng địa chỉ có offset +4784.
    + Ví dụ: xr0 = adr_of [+4784] gay , 0x01 , 0x30'''
    },

    'key_cmp': {
        'title': '15. Xử lý phím với getkey và cmp_ea',
        'content': '''+-----------------------------------------------------------------------------+
| 15. Xử lý phím với getkey và cmp_ea                                          |
+-----------------------------------------------------------------------------+

Để chương trình phản hồi theo phím bấm, ta kết hợp getkey để lấy keycode KI/KO, dùng cmp_ea so sánh với bảng, và nhảy đến nhánh xử lý tương ứng.

Cấu trúc chung:
```asm
setup_key:
    er0 = adr_of key
    getkey # hoặc các hàm đọc phím khác tuỳ mục đích sử dụng
    setlr
    pop er0
key:
    hex 00 00
    ea = adr_of table
    cmp_ea
    er6 = [ea]          # 1C64A
    sp = er6, pop er8   # 21F74

func_1:
    # xử lý khi nhấn phím 1
    goto loop

func_2:
    # xử lý khi nhấn phím 2
    goto loop

# các phím khác

loop:
    # loop :)

table:
    0x0101                  # keycode phím 1
    adr_of [-2] func1       # địa chỉ nhánh (trừ 2 do pop er8)
    hex 0x0102              # keycode phím 2
    adr_of [-2] func2
    # ... các phím khác
    0x0000                  # kết thúc bảng
    adr_of [-2] loop        # nhánh mặc định (thường là loop)
```

Giải thích:
  - getkey đọc phím, lưu KI/KO (2 byte) vào key.
  - pop er0 lấy giá trị key vừa đọc vào er0 (cần thiết vì getkey có thể làm thay đổi er0).
  - cmp_ea so sánh er0 với các mục trong bảng. Nếu tìm thấy, ea trỏ đến địa chỉ nhánh tương ứng (2 byte sau keycode).
  - er6 = [ea] lấy địa chỉ nhánh vào er6.
  - sp = er6, pop er8 (gadget 21F74) thực hiện:
      mov sp, er6         (đặt SP = er6)
      pop er8             (lấy 2 byte từ SP vào er8, SP tăng 2)
      pop pc              (lấy 2 byte tiếp theo vào PC, SP tăng 2)
  - Do có pop er8 trước, địa chỉ nhảy phải được đặt trừ đi 2 (adr_of [-2]). Như vậy, sau khi pop er8, SP sẽ trỏ đúng đến địa chỉ nhảy và pop pc sẽ nhảy đến đó.

Ví dụ: ấn 1 , 2 để hiện text
```asm
org 0xd730
home:
    setlr
    setsfr
    buffer_clear
setup_key:
    er0 = adr_of key
    getkey
    setlr
    pop er0
key:
    0x0000
    ea = adr_of table
    cmp_ea
    er6 = [ea]
    sp = er6, pop er8
print1:
    xr0 = 0x301a, adr_of text1
    printline
    render.ddd4
    goto loop
print2:
    xr0 = 0x301a, adr_of text2
    printline
    render.ddd4
    goto loop
loop:
    xr0 = 0xd184d630
    BL strcpy
    er14 = 0xd62e
    sp=er14,pop er14
table:
    hex 01 01
    adr_of [-2] print1
    hex 01 02
    adr_of [-2] print2
    hex 00 00
    adr_of [-2] loop
text1:
    str"11111111111111111"
text2:
    str"22222222222222222"
```

Lưu ý:
  - Bảng phải kết thúc bằng 0x0000 và địa chỉ mặc định.
  - Các nhánh xử lý nên kết thúc bằng goto loop

Verify kết hợp với cmp_ea

Trong các phần mềm, đôi khi ta không chỉ muốn so sánh bằng mà còn muốn so sánh các điều kiện khác. Khi ấy ta sử dụng các hàm có sẵn từ chế độ verify của máy.

Các hàm verify:
```asm
- 0x19536 : verify_eq   (==)
- 0x195C0 : verify_ne   (!=)
- 0x19516 : verify_gt   (>)
- 0x19526 : verify_lt   (<)
- 0x194F6 : verify_ge   (>=)
- 0x19506 : verify_le   (<=)
```

Cách gọi:
```asm
xr0 = <địa chỉ 1>, <địa chỉ 2>
call <verify function>
```

Kết quả trả về: er0 = hex 00 01 và hex er2 = 01 00 nếu đúng (True), còn sai (False) thì er0 = er2 = 00 00. Từ đấy ta có thể sử dụng cmp_ea để thực hiện các loại so sánh.

Chẳng hạn:
```asm
a:
    [...]
b:
    [...]
verify:
    xr0 = adr_of a, adr_of b
    call 195c0 # verify_ne (!=), kiểm tra xem a!=b hay không.
    ea = adr_of table
    cmp_ea
    er6 = [ea]
    sp = er6, pop er8
if_ne:
    [...]
else:
    [...]
table:
    hex 00 01
    adr_of [-2] if_ne
    hex 00 00
    adr_of [-2] else
```

Cách sử dụng tương tự với các hàm verify khác.'''
    },
}


def _split_blocks(content):
    blocks = []
    cur_text = []
    cur_code = []
    in_fence = False
    for line in content.split('\n'):
        if line.startswith('```'):
            if in_fence:
                blocks.append(('code', '\n'.join(cur_code)))
                cur_code = []
                in_fence = False
            else:
                blocks.append(('text', '\n'.join(cur_text)))
                cur_text = []
                in_fence = True
        elif in_fence:
            cur_code.append(line)
        else:
            cur_text.append(line)
    if cur_text:
        blocks.append(('text', '\n'.join(cur_text)))
    if cur_code:
        blocks.append(('code', '\n'.join(cur_code)))
    return blocks


def chunk_text(text, limit=1900):
    chunks = []
    cur = ''
    for kind, blk in _split_blocks(text):
        if kind == 'code':
            blk = '```\n' + blk + '\n```'
        if cur and len(cur) + len(blk) + 1 > limit:
            chunks.append(cur)
            cur = blk
        else:
            cur = cur + '\n' + blk if cur else blk
        while len(cur) > limit:
            cut = cur.rfind('\n', 0, limit)
            if cut <= 0:
                cut = limit
            chunks.append(cur[:cut].rstrip())
            cur = cur[cut:].lstrip('\n')
    if cur:
        chunks.append(cur)
    return chunks