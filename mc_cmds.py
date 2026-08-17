DATA = {
    'cat1': {
        'title': '1. Quản lý Thế giới & Môi trường',
        'content': '''+-----------------------------------------------------------------------------+
| 1. Nhóm Quản lý Thế giới & Môi trường                                         |
+-----------------------------------------------------------------------------+

Các lệnh dùng để điều khiển thời gian, thời tiết, thế giới và quy tắc game (Gamerule).
```hs
/gamerule <tên_quy_tắc> [<giá_trị>]    # Bật/tắt hoặc chỉnh sửa quy tắc game (VD: keepInventory, doDaylightCycle)
/time <set|add|query> <giá_trị>         # Thay đổi hoặc xem thời gian trong thế giới (day, night, 1000)
/weather <clear|rain|thunder> [<thời_gian>]  # Đổi thời tiết và thời lượng kéo dài
/difficulty [peaceful|easy|normal|hard] # Đổi độ khó của thế giới
/worldborder <set|add|center|damage|warning...>  # Tùy chỉnh đường biên giới thế giới
/defaultgamemode <survival|creative|adventure|spectator>  # Chế độ mặc định cho người mới vào
/seed                                # Xem mã Seed của thế giới
/place <feature|structure|template|jigsaw...>  # Đặt công trình/đặc tính địa hình vào vị trí
```'''
    },
    'cat2': {
        'title': '2. Người chơi & Thực thể',
        'content': '''+-----------------------------------------------------------------------------+
| 2. Nhóm Người chơi & Thực thể (Entities)                                      |
+-----------------------------------------------------------------------------+

Các lệnh tác động lên bản thân, người chơi khác hoặc mob/thực thể.
```hs
/gamemode <survival|creative|adventure|spectator> [<đối_tượng>]  # Đổi chế độ chơi
/tp hoặc /teleport <vị_trí_đích>      # Dịch chuyển thực thể/người chơi
/kill [<đối_tượng>]                    # Tiêu diệt thực thể/người chơi
/summon <thực_thể> [<tọa_độ>] [<nbt>] # Triệu hồi mob/thực thể (Xe mỏ, Khung tranh, TNT...)
/effect <give|clear> <đối_tượng> <hiệu_ứng> [<thời_gian>] [<cấp_độ>]  # Cấp/xóa hiệu ứng
/attribute <đối_tượng> <thuộc_tính> <hành_động>  # Đọc/chỉnh chỉ số gốc (Máu, Tốc độ, Sát thương, generic.scale)
/damage <đối_tượng> <số_lượng> [<loại_sát_thương>]  # Gây sát thương trực tiếp
/experience hoặc /xp <add|set|query> <đối_tượng> <số_lượng>  # Thêm/đặt/xem kinh nghiệm
/spectate [<mục_tiêu>] [<người_xem>]  # Spectator nhập góc nhìn thực thể khác
/ride <thực_thể> mount|dismount <thực_thể_khác>  # Bắt buộc cưỡi lên/leo xuống
```'''
    },
    'cat3': {
        'title': '3. Vật phẩm & Túi đồ',
        'content': '''+-----------------------------------------------------------------------------+
| 3. Nhóm Vật phẩm & Túi đồ (Inventory)                                         |
+-----------------------------------------------------------------------------+
```hs
/give <đối_tượng> <item> [<số_lượng>]  # Cho người chơi vật phẩm
/clear [<đối_tượng>] [<item>] [<số_lượng>]  # Xóa vật phẩm trong túi đồ
/item <replace|modify> ...              # Thay thế/chỉnh sửa vật phẩm trong túi, rương, tay
/enchant <đối_tượng> <phù_phép> [<cấp_độ>]  # Phù phép vật phẩm đang cầm
/loot <hướng_dán> <nguồn_loot>          # Bỏ đồ rơi ra từ cá thể/rương/bảng loot
```'''
    },
    'cat4': {
        'title': '4. Khối & Cấu trúc',
        'content': '''+-----------------------------------------------------------------------------+
| 4. Nhóm Khối & Cấu trúc (Blocks & Construction)                               |
+-----------------------------------------------------------------------------+
```hs
/setblock <x y z> <tên_khối> [destroy|keep|replace]  # Đặt khối tại tọa độ
/fill <x1 y1 z1> <x2 y2 z2> <tên_khối> [replace|outline...]  # Lấp đầy khu vực bằng khối
/fillbiome <x1 y1 z1> <x2 y2 z2> <tên_biome>  # Đổi Biome của khu vực
/clone <x1 y1 z1> <x2 y2 z2> <x3 y3 z3> ...  # Sao chép khu vực khối
/structure <save|load|delete...>        # Lưu/tải cấu trúc (Structure Block)
```'''
    },
    'cat5': {
        'title': '5. Lập trình, Command Block & Datapack',
        'content': '''+-----------------------------------------------------------------------------+
| 5. Nhóm Lập trình, Command Block & Datapack                                   |
+-----------------------------------------------------------------------------+

Nhóm lệnh cao cấp cho người làm Map, Custom, Datapack.
```hs
/execute ...  # Lệnh mạnh nhất: thực thi theo điều kiện, tọa độ, thực thể, hướng
/data <get|merge|modify|remove> ...  # Đọc/chỉnh sửa NBT/Component
/scoreboard <objectives|players> ... # Quản lý bảng điểm (tạo biến, lưu dữ liệu)
/bossbar <add|remove|set|get> ...    # Tạo/quản lý thanh Bossbar
/function <tên_hàm>                  # Chạy chuỗi lệnh trong file Datapack
/tag <đối_tượng> <add|remove|list> <tên_tag>  # Gán thẻ phân loại thực thể
/team <add|remove|join|leave|option...>  # Tạo/quản lý đội chơi
/advancement <grant|revoke> ...      # Cấp/xóa thành tựu
/recipe <give|take> <đối_tượng> <công_thức|*>  # Cho/xóa công thức chế tạo
/schedule <function|clear> <thời_gian>  # Lên lịch chạy function
/trigger <tên_mục_tiêu>              # Người không admin kích hoạt Scoreboard được phép
```'''
    },
    'cat6': {
        'title': '6. Hệ thống, Máy chủ & Thông báo',
        'content': '''+-----------------------------------------------------------------------------+
| 6. Nhóm Hệ thống, Máy chủ & Thông báo                                         |
+-----------------------------------------------------------------------------+
```hs
/say <tin_nhắn>                       # Đưa thông điệp ra chat chung
/tell hoặc /w hoặc /msg <đối_tượng> <tin_nhắn>  # Nhắn riêng cho ai đó
/title <đối_tượng> <title|subtitle|actionbar|clear...> <JSON>  # Chữ lớn trên màn hình
/tellraw <đối_tượng> <JSON>           # Gửi chat dạng JSON (click/hover/màu)
/playsound <âm_thanh> <nguồn> <đối_tượng> [<tọa_độ>]  # Phát âm thanh
/stopsound <đối_tượng> [<nguồn>] [<âm_thanh>]  # Tắt âm thanh
/particle <tên_hạt> [<tọa_độ>] [<kích_thước>] [<số_lượng>]  # Tạo hiệu ứng hạt
/locate <structure|biome|poi> <tên_cần_tìm>  # Tìm tọa độ công trình/biome/điểm quan tâm
/reload                            # Tải lại Datapack & Loot table
/datapack <enable|disable|list>    # Quản lý gói Datapack
/op <người_chơi> / /deop <người_chơi>  # Cấp/tước quyền Admin
/ban, /pardon, /kick               # Cấm, bỏ cấm, đuổi khỏi server
/whitelist <add|remove|on|off>     # Quản lý người chơi cho phép vào server
/tick <query|rate|freeze|step...>  # Điều khiển tick rate (làm chậm/đóng băng/tăng tốc) (1.20.3+)
```'''
    },
}