/* বিন্দাজ Buildz build engine: parts data + compatibility + build search.
   Runs in the browser (window.BB) and in Node (globalThis.BB) for precomputed ready builds. */
(function(root){
const C=[ // cpu: s socket, g gaming, c productivity, w watts, ig integrated graphics, cool stock cooler, t recommended board tier (1 entry A/H, 2 mainstream B-M, 3 upper B, 4 X/Z)
{id:'r5-5500',n:'AMD Ryzen 5 5500',b:'amd',s:'AM4',p:9500,g:45,c:35,w:65,ig:0,cool:1,t:1,mem:'DDR4',sp:'6C/12T, up to 4.2 GHz'},
{id:'r5-5600',n:'AMD Ryzen 5 5600',b:'amd',s:'AM4',p:13500,g:52,c:40,w:65,ig:0,cool:1,t:1,mem:'DDR4',sp:'6C/12T, up to 4.4 GHz'},
{id:'r5-5600g',n:'AMD Ryzen 5 5600G',b:'amd',s:'AM4',p:15000,g:46,c:38,w:65,ig:1,cool:1,t:1,mem:'DDR4',sp:'6C/12T with Radeon Vega 7 graphics'},
{id:'r5-5600gt',n:'AMD Ryzen 5 5600GT',b:'amd',s:'AM4',p:14000,g:47,c:39,w:65,ig:1,cool:1,t:1,mem:'DDR4',sp:'6C/12T with Radeon graphics'},
{id:'r5-5600x',n:'AMD Ryzen 5 5600X',b:'amd',s:'AM4',p:15500,g:54,c:42,w:65,ig:0,cool:1,t:1,mem:'DDR4',sp:'6C/12T, up to 4.6 GHz'},
{id:'r7-5700x',n:'AMD Ryzen 7 5700X',b:'amd',s:'AM4',p:19000,g:55,c:52,w:65,ig:0,cool:0,t:2,mem:'DDR4',sp:'8C/16T, up to 4.6 GHz'},
{id:'r7-5800x',n:'AMD Ryzen 7 5800X',b:'amd',s:'AM4',p:24000,g:58,c:55,w:105,ig:0,cool:0,t:2,mem:'DDR4',sp:'8C/16T, up to 4.7 GHz'},
{id:'r7-5700x3d',n:'AMD Ryzen 7 5700X3D',b:'amd',s:'AM4',p:25000,g:68,c:52,w:105,ig:0,cool:0,t:2,mem:'DDR4',sp:'8C/16T, 96 MB 3D V-Cache'},
{id:'r5-8500g',n:'AMD Ryzen 5 8500G',b:'amd',s:'AM5',p:17000,g:48,c:42,w:65,ig:1,cool:1,t:1,mem:'DDR5',sp:'6 cores with Radeon 740M graphics'},
{id:'r5-7500f',n:'AMD Ryzen 5 7500F',b:'amd',s:'AM5',p:18500,g:64,c:53,w:65,ig:0,cool:1,t:1,mem:'DDR5',sp:'6C/12T, no built-in graphics'},
{id:'r5-9500f',n:'AMD Ryzen 5 9500F',b:'amd',s:'AM5',p:22000,g:68,c:56,w:65,ig:0,cool:1,t:1,mem:'DDR5',sp:'6C/12T Zen 5, no built-in graphics'},
{id:'r5-7600',n:'AMD Ryzen 5 7600',b:'amd',s:'AM5',p:23500,g:67,c:55,w:65,ig:1,cool:1,t:1,mem:'DDR5',sp:'6C/12T, up to 5.1 GHz'},
{id:'r5-8600g',n:'AMD Ryzen 5 8600G',b:'amd',s:'AM5',p:24000,g:58,c:50,w:65,ig:1,cool:1,t:1,mem:'DDR5',sp:'6C/12T with Radeon 760M graphics'},
{id:'r5-9600',n:'AMD Ryzen 5 9600',b:'amd',s:'AM5',p:25500,g:70,c:58,w:65,ig:1,cool:1,t:1,mem:'DDR5',sp:'6C/12T Zen 5, boxed cooler'},
{id:'r5-9600x',n:'AMD Ryzen 5 9600X',b:'amd',s:'AM5',p:27500,g:72,c:60,w:65,ig:1,cool:0,t:2,mem:'DDR5',sp:'6C/12T Zen 5, up to 5.4 GHz'},
{id:'r7-7700',n:'AMD Ryzen 7 7700',b:'amd',s:'AM5',p:32000,g:72,c:70,w:65,ig:1,cool:1,t:2,mem:'DDR5',sp:'8C/16T, boxed cooler'},
{id:'r7-7700x',n:'AMD Ryzen 7 7700X',b:'amd',s:'AM5',p:34000,g:73,c:71,w:105,ig:1,cool:0,t:2,mem:'DDR5',sp:'8C/16T, up to 5.4 GHz'},
{id:'r7-8700g',n:'AMD Ryzen 7 8700G',b:'amd',s:'AM5',p:35000,g:62,c:64,w:65,ig:1,cool:1,t:2,mem:'DDR5',sp:'8C/16T with Radeon 780M graphics'},
{id:'r7-9700x',n:'AMD Ryzen 7 9700X',b:'amd',s:'AM5',p:38000,g:76,c:74,w:88,ig:1,cool:0,t:2,mem:'DDR5',sp:'8C/16T Zen 5, up to 5.5 GHz'},
{id:'r9-7900x',n:'AMD Ryzen 9 7900X',b:'amd',s:'AM5',p:42000,g:75,c:85,w:170,ig:1,cool:0,t:3,mem:'DDR5',sp:'12C/24T, up to 5.6 GHz'},
{id:'r7-7800x3d',n:'AMD Ryzen 7 7800X3D',b:'amd',s:'AM5',p:47000,g:90,c:68,w:120,ig:1,cool:0,t:2,mem:'DDR5',sp:'8C/16T, 96 MB 3D V-Cache'},
{id:'r9-9900x',n:'AMD Ryzen 9 9900X',b:'amd',s:'AM5',p:50000,g:78,c:88,w:120,ig:1,cool:0,t:3,mem:'DDR5',sp:'12C/24T, up to 5.6 GHz'},
{id:'r7-9800x3d',n:'AMD Ryzen 7 9800X3D',b:'amd',s:'AM5',p:60000,g:100,c:80,w:120,ig:1,cool:0,t:3,mem:'DDR5',sp:'8C/16T, fastest gaming CPU'},
{id:'r9-9950x',n:'AMD Ryzen 9 9950X',b:'amd',s:'AM5',p:68000,g:80,c:100,w:170,ig:1,cool:0,t:3,mem:'DDR5',sp:'16C/32T, up to 5.7 GHz'},
{id:'r9-9950x3d',n:'AMD Ryzen 9 9950X3D',b:'amd',s:'AM5',p:85000,g:100,c:100,w:170,ig:1,cool:0,t:3,mem:'DDR5',sp:'16C/32T with 3D V-Cache'},
{id:'i3-12100',n:'Intel Core i3-12100',b:'intel',s:'LGA1700',p:12500,g:42,c:28,w:60,ig:1,cool:1,t:1,mem:'both',sp:'4C/8T with UHD 730 graphics'},
{id:'i5-12400f',n:'Intel Core i5-12400F',b:'intel',s:'LGA1700',p:13000,g:52,c:40,w:65,ig:0,cool:1,t:1,mem:'both',sp:'6C/12T, up to 4.4 GHz'},
{id:'i3-14100',n:'Intel Core i3-14100',b:'intel',s:'LGA1700',p:15000,g:46,c:32,w:60,ig:1,cool:1,t:1,mem:'both',sp:'4C/8T with UHD 730 graphics'},
{id:'i5-12400',n:'Intel Core i5-12400',b:'intel',s:'LGA1700',p:16000,g:52,c:40,w:65,ig:1,cool:1,t:1,mem:'both',sp:'6C/12T with UHD 730 graphics'},
{id:'i5-13400f',n:'Intel Core i5-13400F',b:'intel',s:'LGA1700',p:20000,g:57,c:52,w:65,ig:0,cool:1,t:2,mem:'both',sp:'10 cores (6P+4E) / 16 threads'},
{id:'i5-14400f',n:'Intel Core i5-14400F',b:'intel',s:'LGA1700',p:22500,g:60,c:55,w:65,ig:0,cool:1,t:2,mem:'both',sp:'10 cores (6P+4E), up to 4.7 GHz'},
{id:'i5-14400',n:'Intel Core i5-14400',b:'intel',s:'LGA1700',p:25500,g:60,c:55,w:65,ig:1,cool:1,t:2,mem:'both',sp:'10 cores with UHD 730 graphics'},
{id:'i5-14600kf',n:'Intel Core i5-14600KF',b:'intel',s:'LGA1700',p:31000,g:73,c:72,w:180,ig:0,cool:0,t:3,mem:'both',sp:'14 cores (6P+8E), unlocked, no graphics'},
{id:'i5-14600k',n:'Intel Core i5-14600K',b:'intel',s:'LGA1700',p:33000,g:73,c:72,w:180,ig:1,cool:0,t:3,mem:'both',sp:'14 cores (6P+8E), unlocked'},
{id:'i7-14700',n:'Intel Core i7-14700',b:'intel',s:'LGA1700',p:40000,g:76,c:84,w:180,ig:1,cool:0,t:3,mem:'both',sp:'20 cores (8P+12E)'},
{id:'i7-14700kf',n:'Intel Core i7-14700KF',b:'intel',s:'LGA1700',p:43000,g:79,c:86,w:250,ig:0,cool:0,t:3,mem:'both',sp:'20 cores, unlocked, no graphics'},
{id:'i7-14700k',n:'Intel Core i7-14700K',b:'intel',s:'LGA1700',p:45000,g:79,c:86,w:250,ig:1,cool:0,t:3,mem:'both',sp:'20 cores (8P+12E), unlocked'},
{id:'i9-14900k',n:'Intel Core i9-14900K',b:'intel',s:'LGA1700',p:58000,g:82,c:92,w:253,ig:1,cool:0,t:4,mem:'both',sp:'24 cores (8P+16E), up to 6.0 GHz'},
{id:'u5-225',n:'Intel Core Ultra 5 225',b:'intel',s:'LGA1851',p:24000,g:60,c:62,w:65,ig:1,cool:1,t:2,mem:'DDR5',sp:'10 cores, Arrow Lake, boxed cooler'},
{id:'u5-245kf',n:'Intel Core Ultra 5 245KF',b:'intel',s:'LGA1851',p:31000,g:68,c:74,w:160,ig:0,cool:0,t:2,mem:'DDR5',sp:'14 cores, no graphics'},
{id:'u5-245k',n:'Intel Core Ultra 5 245K',b:'intel',s:'LGA1851',p:33000,g:68,c:74,w:160,ig:1,cool:0,t:2,mem:'DDR5',sp:'14 cores, Arrow Lake, built-in NPU'},
{id:'u7-265kf',n:'Intel Core Ultra 7 265KF',b:'intel',s:'LGA1851',p:40000,g:73,c:88,w:200,ig:0,cool:0,t:3,mem:'DDR5',sp:'20 cores, no graphics'},
{id:'u7-265k',n:'Intel Core Ultra 7 265K',b:'intel',s:'LGA1851',p:42000,g:73,c:88,w:200,ig:1,cool:0,t:3,mem:'DDR5',sp:'20 cores, Arrow Lake'},
{id:'u9-285k',n:'Intel Core Ultra 9 285K',b:'intel',s:'LGA1851',p:62000,g:77,c:99,w:250,ig:1,cool:0,t:4,mem:'DDR5',sp:'24 cores, Arrow Lake flagship'}];
const G=[
{id:'none',n:'No graphics card',b:'none',p:0,g:6,c:4,w:0,sp:'Uses the processor’s built-in graphics'},
{id:'gtx1650',n:'NVIDIA GTX 1650 4GB',b:'nvidia',p:18000,g:14,c:12,w:75,sp:'4 GB GDDR6, no power cable'},
{id:'rtx3050',n:'NVIDIA RTX 3050 6GB',b:'nvidia',p:26000,g:20,c:18,w:70,sp:'6 GB GDDR6, no power cable'},
{id:'rtx5050',n:'NVIDIA RTX 5050 8GB',b:'nvidia',p:36000,g:34,c:32,w:130,sp:'8 GB GDDR6, DLSS 4'},
{id:'rtx3060',n:'NVIDIA RTX 3060 12GB',b:'nvidia',p:38000,g:38,c:40,w:170,sp:'12 GB GDDR6'},
{id:'rtx4060',n:'NVIDIA RTX 4060 8GB',b:'nvidia',p:40000,g:42,c:40,w:115,sp:'8 GB GDDR6, DLSS 3'},
{id:'rtx5060',n:'NVIDIA RTX 5060 8GB',b:'nvidia',p:44000,g:45,c:42,w:145,sp:'8 GB GDDR7, DLSS 4 frame generation'},
{id:'rtx5060ti8',n:'NVIDIA RTX 5060 Ti 8GB',b:'nvidia',p:58000,g:52,c:50,w:180,sp:'8 GB GDDR7'},
{id:'rtx5060ti16',n:'NVIDIA RTX 5060 Ti 16GB',b:'nvidia',p:72000,g:55,c:58,w:180,sp:'16 GB GDDR7, roomy for editing'},
{id:'rtx5070',n:'NVIDIA RTX 5070 12GB',b:'nvidia',p:94000,g:68,c:70,w:250,sp:'12 GB GDDR7'},
{id:'rtx5070ti',n:'NVIDIA RTX 5070 Ti 16GB',b:'nvidia',p:135000,g:82,c:84,w:300,big:1,sp:'16 GB GDDR7'},
{id:'rtx5080',n:'NVIDIA RTX 5080 16GB',b:'nvidia',p:190000,g:92,c:92,w:360,big:1,sp:'16 GB GDDR7'},
{id:'rtx5090',n:'NVIDIA RTX 5090 32GB',b:'nvidia',p:420000,g:100,c:100,w:575,big:1,sp:'32 GB GDDR7, flagship'},
{id:'rx6600',n:'AMD Radeon RX 6600 8GB',b:'amd',p:30000,g:30,c:20,w:132,sp:'8 GB GDDR6'},
{id:'rx7600',n:'AMD Radeon RX 7600 8GB',b:'amd',p:36000,g:37,c:24,w:165,sp:'8 GB GDDR6'},
{id:'rx7600xt',n:'AMD Radeon RX 7600 XT 16GB',b:'amd',p:42000,g:40,c:30,w:190,sp:'16 GB GDDR6'},
{id:'rx9060xt8',n:'AMD Radeon RX 9060 XT 8GB',b:'amd',p:46000,g:52,c:38,w:160,sp:'8 GB GDDR6, FSR 4'},
{id:'rx7700xt',n:'AMD Radeon RX 7700 XT 12GB',b:'amd',p:55000,g:58,c:42,w:245,sp:'12 GB GDDR6'},
{id:'rx9060xt16',n:'AMD Radeon RX 9060 XT 16GB',b:'amd',p:58000,g:55,c:44,w:180,sp:'16 GB GDDR6, FSR 4'},
{id:'rx7800xt',n:'AMD Radeon RX 7800 XT 16GB',b:'amd',p:70000,g:66,c:50,w:263,sp:'16 GB GDDR6'},
{id:'rx9070',n:'AMD Radeon RX 9070 16GB',b:'amd',p:92000,g:72,c:58,w:220,sp:'16 GB GDDR6, FSR 4'},
{id:'rx9070xt',n:'AMD Radeon RX 9070 XT 16GB',b:'amd',p:105000,g:78,c:62,w:304,big:1,sp:'16 GB GDDR6, FSR 4'},
{id:'arca750',n:'Intel Arc A750 8GB',b:'intel',p:28000,g:33,c:28,w:225,sp:'8 GB GDDR6'},
{id:'arcb570',n:'Intel Arc B570 10GB',b:'intel',p:33000,g:39,c:32,w:150,sp:'10 GB GDDR6'},
{id:'arcb580',n:'Intel Arc B580 12GB',b:'intel',p:40000,g:44,c:36,w:190,sp:'12 GB GDDR6'}];
const B=[ // t: 1 entry, 2 mainstream, 3 upper, 4 enthusiast
{id:'a520m-k',ent:1,n:'Gigabyte A520M K V2',s:'AM4',mem:'DDR4',t:1,p:8800,sp:'A520, mATX, DDR4'},
{id:'a520m-a',ent:1,n:'MSI A520M-A Pro',s:'AM4',mem:'DDR4',t:1,p:9500,sp:'A520, mATX, DDR4'},
{id:'b450m',n:'MSI B450M-A Pro Max II',s:'AM4',mem:'DDR4',t:1,p:10000,sp:'B450, mATX, DDR4'},
{id:'b550m-ds3h',n:'Gigabyte B550M DS3H',s:'AM4',mem:'DDR4',t:2,p:14000,sp:'B550, mATX, PCIe 4.0'},
{id:'b550m-wifi',n:'MSI B550M Pro-VDH WiFi',s:'AM4',mem:'DDR4',t:2,p:17500,sp:'B550, mATX, Wi-Fi'},
{id:'b550-tom',n:'MSI MAG B550 Tomahawk Max WiFi',s:'AM4',mem:'DDR4',t:3,p:21000,atx:1,sp:'B550, ATX, Wi-Fi 6, strong VRM'},
{id:'b550-tuf',n:'ASUS TUF Gaming B550-Plus WiFi II',s:'AM4',mem:'DDR4',t:3,p:22500,atx:1,sp:'B550, ATX, Wi-Fi 6'},
{id:'a620m-hdv',ent:1,n:'ASRock A620M-HDV/M.2+',s:'AM5',mem:'DDR5',t:1,p:13000,sp:'A620, mATX, DDR5'},
{id:'a620m-gx',ent:1,n:'Gigabyte A620M Gaming X',s:'AM5',mem:'DDR5',t:1,p:14500,sp:'A620, mATX, DDR5'},
{id:'b650m-d3hp',n:'Gigabyte B650M D3HP',s:'AM5',mem:'DDR5',t:2,p:18500,sp:'B650, mATX, PCIe 4.0'},
{id:'b650m-gp',n:'MSI B650M Gaming Plus WiFi',s:'AM5',mem:'DDR5',t:2,p:21000,sp:'B650, mATX, Wi-Fi 6E'},
{id:'b650m-tuf',n:'ASUS TUF Gaming B650M-E WiFi',s:'AM5',mem:'DDR5',t:2,p:22500,sp:'B650, mATX, Wi-Fi 6'},
{id:'b850m-gp',n:'MSI B850M Gaming Plus WiFi',s:'AM5',mem:'DDR5',t:3,p:25000,sp:'B850, mATX, Wi-Fi 7, PCIe 5.0 SSD'},
{id:'b650-eagle',n:'Gigabyte B650 Eagle AX',s:'AM5',mem:'DDR5',t:3,p:25500,atx:1,sp:'B650, ATX, Wi-Fi 6E'},
{id:'b850-tuf',n:'ASUS TUF Gaming B850-Plus WiFi',s:'AM5',mem:'DDR5',t:3,p:30000,atx:1,sp:'B850, ATX, Wi-Fi 7'},
{id:'x870-tuf',n:'ASUS TUF Gaming X870-Plus WiFi',s:'AM5',mem:'DDR5',t:4,p:40000,atx:1,sp:'X870, ATX, Wi-Fi 7, USB4'},
{id:'x870e-tom',n:'MSI MAG X870E Tomahawk WiFi',s:'AM5',mem:'DDR5',t:4,p:52000,atx:1,sp:'X870E, ATX, PCIe 5.0 GPU + SSD'},
{id:'h610m-e',n:'MSI Pro H610M-E DDR4',s:'LGA1700',mem:'DDR4',t:1,p:9800,sp:'H610, mATX, DDR4'},
{id:'h610m-s2h',n:'Gigabyte H610M S2H DDR4',s:'LGA1700',mem:'DDR4',t:1,p:10000,sp:'H610, mATX, DDR4'},
{id:'b760m-e4',n:'MSI Pro B760M-E DDR4',s:'LGA1700',mem:'DDR4',t:2,p:14000,sp:'B760, mATX, DDR4'},
{id:'b760m-ds3h4',n:'Gigabyte B760M DS3H DDR4',s:'LGA1700',mem:'DDR4',t:2,p:15500,sp:'B760, mATX, DDR4, PCIe 4.0'},
{id:'b760m-gx5',n:'Gigabyte B760M Gaming X AX',s:'LGA1700',mem:'DDR5',t:2,p:20000,sp:'B760, mATX, DDR5, Wi-Fi 6E'},
{id:'b760m-tuf4',n:'ASUS TUF Gaming B760M-Plus WiFi D4',s:'LGA1700',mem:'DDR4',t:3,p:20000,sp:'B760, mATX, DDR4, strong VRM'},
{id:'b760m-tuf5',n:'ASUS TUF Gaming B760M-Plus WiFi',s:'LGA1700',mem:'DDR5',t:3,p:22000,sp:'B760, mATX, DDR5, strong VRM'},
{id:'b760-gp',n:'MSI B760 Gaming Plus WiFi',s:'LGA1700',mem:'DDR5',t:3,p:24000,atx:1,sp:'B760, ATX, DDR5, Wi-Fi 6E'},
{id:'z790-p4',n:'MSI Pro Z790-P WiFi DDR4',s:'LGA1700',mem:'DDR4',t:4,p:29000,atx:1,sp:'Z790, ATX, DDR4, overclocking'},
{id:'z790-p',n:'MSI Pro Z790-P WiFi',s:'LGA1700',mem:'DDR5',t:4,p:30000,atx:1,sp:'Z790, ATX, DDR5, overclocking'},
{id:'z790-tuf',n:'ASUS TUF Gaming Z790-Plus WiFi',s:'LGA1700',mem:'DDR5',t:4,p:36000,atx:1,sp:'Z790, ATX, DDR5, Wi-Fi 6'},
{id:'b860m-gx',n:'Gigabyte B860M Gaming X',s:'LGA1851',mem:'DDR5',t:2,p:20000,sp:'B860, mATX, DDR5'},
{id:'b860m-a',n:'MSI Pro B860M-A WiFi',s:'LGA1851',mem:'DDR5',t:2,p:22000,sp:'B860, mATX, Wi-Fi 6E'},
{id:'b860-eagle',n:'Gigabyte B860 Eagle WiFi6E',s:'LGA1851',mem:'DDR5',t:3,p:28000,atx:1,sp:'B860, ATX, Wi-Fi 6E'},
{id:'z890-a',n:'MSI Pro Z890-A WiFi',s:'LGA1851',mem:'DDR5',t:4,p:36000,atx:1,sp:'Z890, ATX, Wi-Fi 7'},
{id:'z890-tuf',n:'ASUS TUF Gaming Z890-Plus WiFi',s:'LGA1851',mem:'DDR5',t:4,p:42000,atx:1,sp:'Z890, ATX, Thunderbolt 4'}];
const R=[
{id:'d4-8',n:'8 GB DDR4-3200 (1×8 GB)',mem:'DDR4',gb:8,p:6500,sp:'Single stick, too little for modern games'},
{id:'d4-16v',n:'16 GB DDR4-3200 (1×16, e.g. Alimoto AmD4H)',mem:'DDR4',gb:16,p:9000,sp:'Single stick, add a second later for dual channel'},
{id:'d4-16',n:'16 GB DDR4-3200 (1×16, e.g. KingBank KJXB)',mem:'DDR4',gb:16,p:12700,sp:'Single stick with heatsink'},
{id:'d4-16x2',n:'16 GB DDR4-3200 (2×8 GB)',mem:'DDR4',gb:16,p:13500,sp:'Dual channel kit'},
{id:'d4-32',n:'32 GB DDR4-3200 (2×16 GB)',mem:'DDR4',gb:32,p:25000,sp:'Dual channel kit'},
{id:'d5-8',n:'8 GB DDR5-5600 (1×8 GB)',mem:'DDR5',gb:8,p:15000,sp:'Single stick, too little for modern games'},
{id:'d5-16',n:'16 GB DDR5-6000 (1×16, e.g. KingBank Soarblade)',mem:'DDR5',gb:16,p:25500,sp:'Single stick, CL36, add a second later'},
{id:'d5-16rgb',n:'16 GB DDR5-6000 RGB (1×16, e.g. Lexar ARES)',mem:'DDR5',gb:16,p:33000,sp:'Single stick with RGB'},
{id:'d5-16x2',n:'16 GB DDR5-6000 (2×8 GB)',mem:'DDR5',gb:16,p:30000,sp:'Dual channel kit'},
{id:'d5-32',n:'32 GB DDR5-6000 (2×16 GB)',mem:'DDR5',gb:32,p:54000,sp:'Dual channel kit, EXPO/XMP'},
{id:'d5-64',n:'64 GB DDR5-6000 (2×32 GB)',mem:'DDR5',gb:64,p:105000,sp:'Dual channel kit, EXPO/XMP'}];
const S=[
{id:'s512',n:'512 GB NVMe Gen3 SSD (e.g. Lexar NM620)',gb:512,p:7000,sp:'~3,300 MB/s',from:0},
{id:'s512g4',n:'512 GB NVMe Gen4 SSD (e.g. Kingston NV3)',gb:512,p:8500,sp:'~5,000 MB/s',from:100000},
{id:'s1t3',n:'1 TB NVMe Gen3 SSD (e.g. Samsung 980)',gb:1000,p:10000,sp:'~3,500 MB/s',from:0},
{id:'s1t4',n:'1 TB NVMe Gen4 SSD (e.g. NCX Dash 4)',gb:1000,p:13000,sp:'~7,500 MB/s',from:100000},
{id:'s1t4p',n:'1 TB NVMe Gen4 SSD (e.g. Samsung 990 Pro)',gb:1000,p:17000,sp:'~7,450 MB/s, DRAM cache',from:250000},
{id:'s2t4',n:'2 TB NVMe Gen4 SSD',gb:2000,p:24000,sp:'~7,000 MB/s',from:0},
{id:'s4t4',n:'4 TB NVMe Gen4 SSD',gb:4000,p:52000,sp:'~7,000 MB/s',from:0}];
const P=[
{id:'p450',n:'450 W 80+ Bronze PSU (e.g. Deepcool PF450)',w:450,p:4800,sp:'Non-modular',from:0},
{id:'p550',n:'550 W 80+ Bronze PSU (e.g. Deepcool PK550D)',w:550,p:6000,sp:'Non-modular',from:0},
{id:'p650',n:'650 W 80+ Bronze PSU (e.g. Deepcool PK650D)',w:650,p:7200,sp:'Non-modular',from:0},
{id:'p750b',n:'750 W 80+ Bronze PSU (e.g. Deepcool PK750D)',w:750,p:9000,sp:'Non-modular',from:0},
{id:'p650g',n:'650 W 80+ Gold PSU (e.g. MSI MAG A650GL)',w:650,p:10000,sp:'Fully modular, ATX 3.1',from:120000},
{id:'p750',n:'750 W 80+ Gold PSU (e.g. MSI MAG A750GL)',w:750,p:12000,sp:'Fully modular, ATX 3.1',from:150000},
{id:'p850',n:'850 W 80+ Gold PSU (e.g. Corsair RM850e)',w:850,p:15500,sp:'Fully modular, ATX 3.1',from:220000},
{id:'p1000',n:'1000 W 80+ Gold PSU (e.g. MSI MPG A1000G)',w:1000,p:21000,sp:'Fully modular, ATX 3.1',from:320000},
{id:'p1200',n:'1200 W 80+ Platinum PSU (e.g. Corsair HX1200i)',w:1200,p:32000,sp:'Fully modular, ATX 3.1',from:450000}];
const K=[
{id:'c1',n:'mATX airflow case, 3 ARGB fans (e.g. Xigmatek Gaming X)',t:1,p:3800,sp:'Fits mATX boards',from:0},
{id:'c2a',n:'Montech X3 Mesh',t:2,atx:1,p:5500,sp:'Mid-tower, 6 fans included',from:70000},
{id:'c2b',n:'Deepcool CC560 V2',t:2,atx:1,p:6500,sp:'Mid-tower, 4 ARGB fans',from:90000},
{id:'c3a',n:'Montech AIR 903 Max',t:3,atx:1,p:9000,sp:'High airflow, 4 × 140 mm fans',from:150000},
{id:'c3b',n:'Lian Li Lancool 207',t:3,atx:1,p:10500,sp:'High airflow, long-GPU clearance',from:180000},
{id:'c4a',n:'Montech King 95 Pro',t:4,atx:1,p:14000,sp:'Dual-chamber panoramic glass',from:260000},
{id:'c4b',n:'Lian Li O11 Dynamic EVO RGB',t:4,atx:1,p:16000,sp:'Dual-chamber, show-off glass',from:320000}];
const Q=[
{id:'stock',n:'Bundled stock cooler',cap:0,p:0,sp:'Comes in the CPU box',from:0},
{id:'q0',n:'Deepcool AG400 air cooler',cap:150,p:2400,sp:'Single tower, 4 heat pipes',from:0},
{id:'q1',n:'Deepcool AK400 air cooler',cap:160,p:2800,sp:'Single tower, 4 heat pipes',from:100000},
{id:'q2a',n:'Thermalright Peerless Assassin 120 SE',cap:220,p:5500,sp:'Dual tower, 6 heat pipes',from:140000},
{id:'q2b',n:'Deepcool AK620',cap:230,p:6500,sp:'Dual tower, 6 heat pipes',from:180000},
{id:'q3',n:'Deepcool LE520 240 mm liquid cooler',cap:230,p:8500,sp:'AIO, ARGB',from:200000},
{id:'q3b',n:'Lian Li Galahad II Trinity 240 liquid cooler',cap:240,p:12000,sp:'AIO, ARGB',from:260000},
{id:'q4b',n:'Arctic Liquid Freezer III 360',cap:330,p:14000,sp:'AIO, thick radiator',from:300000},
{id:'q4',n:'Deepcool LT720 360 mm liquid cooler',cap:320,p:15000,sp:'AIO, ARGB',from:320000}];
const D={cpu:C,gpu:G,board:B,ram:R,ssd:S,psu:P,case:K,cooler:Q};
const LAB={cpu:'Processor',gpu:'Graphics',board:'Motherboard',ram:'Memory',ssd:'Storage',psu:'Power supply',case:'Case',cooler:'CPU cooler'};
const SLOTS=['cpu','gpu','board','ram','ssd','psu','case','cooler'];
const BB={C,G,B,R,S,P,K,Q,D,LAB,SLOTS,LIVE:{},META:null,CAT:[],OV:{},AFF:{},
 opt:{stockOnly:true,ram:0,ssd:0,cpu:'any',gpu:'any',avoidA:true}};
const O=BB.opt;
const isFixed=x=>x.id==='none'||x.id==='stock';
const pr=BB.pr=x=>BB.OV[x.id]??(x.live?x.p:BB.LIVE[x.id]?.price??x.p);
const inStock=BB.inStock=x=>x.live?x.st!==0:isFixed(x)?true:BB.META?!!BB.LIVE[x.id]?.stock:true;
const avail=BB.avail=x=>!O.stockOnly||inStock(x)||isFixed(x);
/* where to buy a part: the shop listing (with affiliate template applied) */
BB.buy=(url,shop)=>{const t=BB.AFF[shop];return t?t.replace('{url_encoded}',encodeURIComponent(url)).replace('{url}',url):url};
BB.listing=o=>{if(isFixed(o))return null;if(o.live)return{url:o.url,shop:o.shop,name:o.n,img:o.img,stock:o.st!==0,price:o.p};
 const l=BB.LIVE[o.id];return l?{url:l.url,shop:l.shop,name:l.name,img:l.img,stock:l.stock,price:l.price}:null};
BB.applyCatalog=function(j){BB.META=j;BB.CAT=j.items||[];const LIVE=BB.LIVE={};
 for(const it of BB.CAT){if(!it.m)continue;const L=LIVE[it.m],st=!!(it.st&&it.p);
  if(!L||(st&&!L.stock)||(st===L.stock&&it.p&&(!L.price||it.p<L.price)))LIVE[it.m]={price:it.p||null,stock:st,shop:it.s,url:it.u,name:it.n,img:it.i||(L&&L.img)}}
 for(const it of BB.CAT){const L=it.m&&LIVE[it.m];if(L&&!L.img&&it.i)L.img=it.i}
 const mk={board:[],ram:[],ssd:[],psu:[],case:[],cooler:[]};
 for(const it of BB.CAT){const a=it.a;if(!a||!it.p||!mk[it.c])continue;
  const o={id:it.id,n:it.n,p:it.p,st:it.st,shop:it.s,url:it.u,img:it.i,live:1};
  if(it.c==='board')Object.assign(o,{s:a.sock,mem:a.mem,t:a.t,atx:a.ff==='ATX'?1:0,ent:/^A\d/.test(a.ch)?1:0,sp:`${a.ch}, ${a.ff}, ${a.mem}${a.wifi?', Wi-Fi':''}`});
  else if(it.c==='ram')Object.assign(o,{mem:a.mem,gb:a.gb,sp:`${a.gb} GB ${a.mem}${a.mhz?'-'+a.mhz:''}, ${a.k} stick${a.k>1?'s':''}`});
  else if(it.c==='ssd'){if(!a.nv)continue;Object.assign(o,{gb:a.gb,sp:`${a.gb>=1000?a.gb/1000+' TB':a.gb+' GB'} NVMe Gen${a.gen}`,from:a.gen>=5?300000:a.gen>=4?100000:0})}
  else if(it.c==='psu'){const g=/Gold|Platinum|Titanium/.test(a.r);Object.assign(o,{w:a.w,sp:`${a.w} W${a.r?' 80+ '+a.r:''}`,from:g?(a.w>=1000?320000:a.w>=850?220000:120000):0})}
  else if(it.c==='case')Object.assign(o,{t:a.t,atx:a.atx,sp:a.atx?'Fits ATX boards':'mATX / ITX boards only',from:[0,0,70000,150000,260000][a.t]});
  else if(it.c==='cooler')Object.assign(o,{cap:a.cap,sp:a.aio?`${a.aio} mm liquid cooler`:a.cap>=200?'Dual-tower air cooler':a.cap<100?'Low-profile air cooler':'Tower air cooler',from:a.cap>=300?280000:a.cap>=230?180000:a.cap>=200?120000:0});
  mk[it.c].push(o)}
 const repl=(arr,list,keep)=>{if(list.length<3)return;const k=arr.filter(keep);arr.length=0;arr.push(...k,...list)};
 repl(B,mk.board,()=>0);repl(R,mk.ram,()=>0);repl(S,mk.ssd,()=>0);repl(P,mk.psu,()=>0);repl(K,mk.case,()=>0);repl(Q,mk.cooler,o=>o.id==='stock')};

/* compatibility */
const need=BB.need=(c,g)=>c.w+g.w+80;
const boardOk=BB.boardOk=(c,b)=>b.s===c.s&&b.t>=c.t&&(c.mem==='both'||c.mem===b.mem);
const boardFit=(c,b)=>boardOk(c,b)&&b.t<=c.t+1;
const psuOk=BB.psuOk=(c,g,p)=>p.w>=need(c,g)*1.4;
const coolOk=BB.coolOk=(c,q)=>q.id==='stock'?(c.cool&&c.w<=125):q.cap>=c.w;
const caseOk=BB.caseOk=(b,g,k)=>(!b.atx||k.atx)&&(!g.big||k.t>=2);
const checks=BB.checks=function(x){const o=[];
 o.push([x.board.s===x.cpu.s,`CPU socket ${x.cpu.s} matches motherboard`]);
 o.push([x.board.t>=x.cpu.t,x.board.t>=x.cpu.t?`${x.board.sp.split(',')[0]} board is the right class for this CPU`:'Board is too basic for this CPU: pick a higher chipset']);
 o.push([x.ram.mem===x.board.mem,`${x.ram.mem} memory fits a ${x.board.mem} board`]);
 const n=need(x.cpu,x.gpu);o.push([psuOk(x.cpu,x.gpu,x.psu),`Estimated draw ~${n} W on a ${x.psu.w} W PSU`]);
 o.push([coolOk(x.cpu,x.cooler),coolOk(x.cpu,x.cooler)?'Cooler handles the CPU’s heat':'Cooler too weak for this CPU']);
 o.push([caseOk(x.board,x.gpu,x.case),caseOk(x.board,x.gpu,x.case)?'Board and graphics card fit the case':'Case too small for board or graphics card']);
 o.push([x.gpu.id!=='none'||x.cpu.ig,x.gpu.id!=='none'?'Display from the graphics card':(x.cpu.ig?'Display from the CPU’s built-in graphics':'This CPU has no built-in graphics: add a card')]);
 return o};
const valid=x=>checks(x).every(c=>c[0]);
const total=BB.total=x=>SLOTS.reduce((s,k)=>s+pr(x[k]),0);

/* build search */
const cheapest=BB.cheapest=(arr,f)=>arr.filter(x=>avail(x)&&f(x)).sort((a,b)=>pr(a)-pr(b))[0];
const MEMO=new Map();const memo=(k,f)=>{let v=MEMO.get(k);if(v===undefined){v=f()??null;MEMO.set(k,v)}return v};
let allowA=false;
const boardUsable=b=>allowA||!O.avoidA||!b.ent;
function minRest(c,g,rq){let best=null;
 const boards=memo('b'+c.id,()=>B.filter(b=>avail(b)&&boardFit(c,b)&&boardUsable(b)));
 const s=memo('s'+rq.ssd,()=>cheapest(S,x=>x.gb===rq.ssd)||cheapest(S,x=>x.gb>=rq.ssd));
 const pw=need(c,g)*1.4,p=memo('p'+pw,()=>cheapest(P,x=>x.w>=pw));
 const q=memo('q'+c.id,()=>cheapest(Q,x=>coolOk(c,x)));
 if(!s||!p||!q)return null;
 for(const b of boards){
  const r=memo('r'+b.mem+rq.ram,()=>cheapest(R,x=>x.mem===b.mem&&x.gb===rq.ram)||cheapest(R,x=>x.mem===b.mem&&x.gb>=rq.ram));if(!r)continue;
  const k=memo('k'+(b.atx?1:0)+(g.big?1:0),()=>cheapest(K,x=>caseOk(b,g,x)));if(!k)continue;
  const t=pr(c)+pr(g)+pr(b)+pr(r)+pr(k)+pr(s)+pr(p)+pr(q);
  if(!best||t<best.t)best={x:{cpu:c,gpu:g,board:b,ram:r,ssd:s,psu:p,case:k,cooler:q},t}}
 return best}
function score(c,g,use){
 if(use==='gaming')return .3*c.g+.7*g.g-Math.max(0,g.g-c.g-25)*.6-(g.id!=='none'?Math.max(0,c.g-g.g-40)*.4:0);
 if(use==='creator')return .5*c.c+.4*g.c+.1*g.g;
 return .85*c.c+.15*c.g+.05*g.g}
function pool(){const cp=O.cpu,gp=O.gpu;
 return[C.filter(c=>c.id===cp||(avail(c)&&(cp==='any'||c.b===cp))),G.filter(g=>g.id===gp||(avail(g)&&(gp==='any'||g.b===gp)))]}
const ORDER={gaming:['psu','cooler','case','board','ssd','case','cooler'],creator:['cooler','psu','board','ssd','case'],office:['case','psu','board','ssd','cooler']};
function upgrade(x,budget,use){
 const cap=budget>=300000?4:budget>=160000?3:budget>=90000?2:1;
 for(const slot of ORDER[use]){const cur=x[slot];
  const cands=D[slot].filter(o=>avail(o)&&pr(o)>pr(cur)&&(o.from||0)<=budget&&(slot!=='board'||(boardFit(x.cpu,o)&&boardUsable(o)&&o.t<=Math.max(x.cpu.t,cap)))&&(slot!=='ssd'||o.gb===cur.gb)).sort((a,b)=>pr(b)-pr(a));
  for(const o of cands){const y={...x,[slot]:o};if(valid(y)&&total(y)<=budget){x=y;break}}}
 return x}
function search(budget,use){MEMO.clear();const[cs,gs]=pool();const rq={ram:O.ram||16,ssd:O.ssd||512};let best=null,minT=Infinity;
 for(const c of cs)for(const g of gs){if(g.id==='none'&&!c.ig)continue;
  const m=minRest(c,g,rq);if(!m)continue;minT=Math.min(minT,m.t);if(m.t>budget)continue;
  const sc=score(c,g,use)-m.t*1e-6;if(!best||sc>best.sc)best={sc,x:m.x}}
 return best?{x:upgrade(best.x,budget,use)}:{min:minT}}
/* A520/A620 boards are used only when nothing else fits the budget */
BB.build=function(budget,use){allowA=false;let r=search(budget,use);if(!r.x&&O.avoidA){allowA=true;r=search(budget,use);allowA=false}return r};
BB.options=function(slot,x){return D[slot].filter(o=>{
 if(slot==='cpu')return o.s===x.board.s&&boardOk(o,x.board);
 if(slot==='board')return boardOk(x.cpu,o)&&(o.mem===x.ram.mem||!!R.find(r=>r.mem===o.mem));
 if(slot==='gpu')return o.id!=='none'||x.cpu.ig;
 if(slot==='psu')return psuOk(x.cpu,x.gpu,o);
 if(slot==='cooler')return coolOk(x.cpu,o);
 if(slot==='case')return caseOk(x.board,x.gpu,o);
 if(slot==='ram')return o.mem===x.board.mem;return true})};
BB.fix=function(x){const msgs=[];
 if(x.ram.mem!==x.board.mem){x.ram=cheapest(R,r=>r.mem===x.board.mem&&r.gb>=x.ram.gb)||cheapest(R,r=>r.mem===x.board.mem);msgs.push('memory switched to '+x.ram.mem)}
 if(!psuOk(x.cpu,x.gpu,x.psu)){x.psu=cheapest(P,p=>psuOk(x.cpu,x.gpu,p));msgs.push('PSU raised to '+x.psu.w+' W')}
 if(!coolOk(x.cpu,x.cooler)){x.cooler=cheapest(Q,q=>coolOk(x.cpu,q));msgs.push('cooler upgraded')}
 if(!caseOk(x.board,x.gpu,x.case)){x.case=cheapest(K,k=>caseOk(x.board,x.gpu,k));msgs.push('bigger case')}
 return msgs};
BB.tier=function(x){const g=x.gpu.g;if(x.gpu.id==='none')return'Office, study, browsing, light esports';
 return g<30?'1080p esports titles':g<46?'1080p high settings':g<60?'1080p ultra, 1440p medium':g<75?'1440p high to ultra':g<90?'1440p ultra, 4K with upscaling':'4K ultra'};
root.BB=BB;
})(typeof window!=='undefined'?window:globalThis);
