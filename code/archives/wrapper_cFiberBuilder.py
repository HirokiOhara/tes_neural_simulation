from neuron import h
from typing import List, Optional

class ThioCFiber:
    '''Thio model のPythonラッパー'''
    
    def __init__(
        self,
        fiber_diameter: float = 6.0,
        length_um: float = 21.0,
        fiber_type: int = 1,
        temperature: float = 37.0,
        seg_density: float = 50/6,
        particle_index: int = 1,
        debug: bool = False
    ):
        self._fiber = h.cFiberBuilder(
            fiber_diameter,     # fiberD
            length_um,          # len
            fiber_type,         # type
            temperature,        # temp
            seg_density,        # segdensity
            particle_index      # ParticleIndex
        )
        
        self._nodes = list(self._fiber.node)
        
        if debug:
            self.print_debug_info()
    
    # ---- プロパティ ----
    
    @property
    def length(self) -> float:
        '''実際の長さ [um]'''
        return self._fiber.Length
    
    @property
    def n_segments(self) -> int:
        '''セグメント数'''
        return int(self._fiber.nsegments)
    
    @property
    def dx(self) -> float:
        '''セグメント長 [um]'''
        return self._fiber.dx
    
    @property
    def diameter(self) -> float:
        '''線維直径 [um]'''
        return self._fiber.fiberD
    
    @property
    def nodes(self) -> List:
        '''全ノードセクションのリスト'''
        return self._nodes
    
    @property
    def section_list(self):
        '''NEURON SectionList'''
        return self._fiber.sl
    
    @property
    def coordinates(self):
        '''各セクションの座標 [m]'''
        return self._fiber.section_coord
    
    # ---- メソッド ----
    
    def get_node(self, index: int):
        '''インデックスでノードを取得'''
        return self._fiber.node[index]
    
    def get_node_at_distance(self, distance_from_end_um: float):
        """
        端からの距離 [um] でノードを取得する。
        distance_from_end_um: 端(0)→反対端(L) の距離
        """
        L = float(self.length)
        d = float(distance_from_end_um)

        # 範囲外はクランプ
        pos_from_left = max(0.0, min(d, L))

        idx = int(pos_from_left / self.dx)
        idx = max(0, min(idx, self.n_segments - 1))
        return self._fiber.node[idx]

    def distance_to_node_center_from_end(self, index: int) -> float:
        """
        指定ノード中心までの端からの距離[um]を返す。
        """
        # section_coord は中心基準 [m]
        x_center_m = float(self.coordinates.x[index])   # node中心の座標（中心基準）
        L_um = float(self.length)
        x_from_left_um = (x_center_m * 1e6) + L_um / 2  # 左端基準へ変換
        return x_from_left_um

    def __iter__(self):
        '''ノードをイテレート'''
        return iter(self._nodes)
    
    def __len__(self):
        return self.n_segments
    
    def __repr__(self):
        return f'ThioCFiber(D={self.diameter}um, L={self.length}um, n={self.n_segments})'
    
if __name__ == '__main__':

    import os
    from pathlib import Path

    PROJECT_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_DIR / 'data'
    MODEL_DIR = DATA_DIR / 'thio-model'
    CONFIG_DIR = DATA_DIR / 'config'
    COMSOL_DIR = DATA_DIR / 'comsol'

    os.chdir(MODEL_DIR)
    h.nrn_load_dll(str(MODEL_DIR / 'nrnmech.dll'))
    h.load_file('nrngui.hoc')
    h.xopen('cFiberBuilder.hoc')
    h.load_file('balance.hoc')

    # 基本的な使用
    fiber = ThioCFiber(length_um=100)

    # パラメータ指定
    fiber01 = ThioCFiber(
        fiber_diameter=0.8,
        length_um=100,
        temperature=37,
        particle_index=1
    )

    print(fiber)

    # パラメータ指定
    fiber02 = ThioCFiber(
        fiber_diameter=0.8,
        length_um=200,
        temperature=37,
        particle_index=1
    )

    print(fiber02)

    # ノードへのアクセス
    for node in fiber:
        print(node.v)

    # 特定位置のノード
    # idx_node = fiber02.get_node_at_distance(50)  # 中心
    # print(idx_node)
    for n in range(len(fiber)):
        dist = fiber.distance_to_node_center_from_end(n)
        print(dist)


    sl = fiber.section_list   # hoc側で作った sl (SectionList)

    # Segmentの確認
    # Thio modelは 1 Segment = 1 Node
    # Segmentは単コンパートメントのこと、Nodeは計算点
    print("n_segments =", fiber.n_segments)
    print("len(section_list) cannot be used directly for SectionList in NEURON")

    print("Iterate SectionList:")
    for i, sec in enumerate(sl):
        print(i, sec.name())

    print("Iterate nodes:")
    for i, sec in enumerate(fiber.nodes):
        print(i, sec.name())

    count = sum(1 for _ in fiber.section_list)
    print("section_list count =", count)

    #==== デバッグモードで生成 ====
    # print('=' * 60)
    # print('テスト1: 短い線維 (21 um)')
    # print('=' * 60)
    # fiber1 = ThioCFiber(length_um=21, debug=True)

    # print('\n\n')

    # print('=' * 60)
    # print('テスト2: 長い線維 (1000 um)')
    # print('=' * 60)
    # fiber2 = ThioCFiber(length_um=1000, debug=True)

    # # 整合性検証
    # fiber2.verify_integrity()
    # fiber2.visualize_structure()
    # ================================


    #==== 詳細デバッグ====
    # fiber = ThioCFiber(length_um=100, debug=False)  # まず短いもので

    # print('=' * 70)
    # print('詳細接続デバッグ')
    # print('=' * 70)

    # fiber.print_detailed_connections()
    # fiber.verify_connection_direction()

    # # h.topology() を直接確認
    # print('\n[NEURON topology() 出力]')
    # h.topology()
    # ================================



    # ---- デバッグメソッド ----
    
    # def print_debug_info(self):
    #     '''全デバッグ情報を出力'''
    #     print('=' * 60)
    #     print('ThioCFiber デバッグ情報')
    #     print('=' * 60)
        
    #     self.print_basic_info()
    #     self.print_topology()
    #     self.print_geometry()
    #     self.print_connections()
    #     self.print_mechanisms()
    #     self.print_coordinates()
        
    #     print('=' * 60)
    
    # def print_basic_info(self):
    #     '''基本情報'''
    #     print('\n[基本パラメータ]')
    #     print(f'  線維直径:     {self.diameter} um')
    #     print(f'  目標長さ:     (入力値)')
    #     print(f'  実際の長さ:   {self.length} um')
    #     print(f'  セグメント数: {self.n_segments}')
    #     print(f'  dx (各セグメント長): {self.dx} um')
    #     print(f'  計算上の総長: {self.n_segments} × {self.dx} = {self.n_segments * self.dx} um')
    
    # def print_topology(self):
    #     '''トポロジー情報'''
    #     print('\n[トポロジー]')
    #     print(f'  node セクション数: {len(self._nodes)}')
        
    #     # h.topology() の出力
    #     print('\n  NEURON topology():')
    #     print('  ' + '-' * 40)
    #     h.topology()
    #     print('  ' + '-' * 40)
    
    # def print_geometry(self):
    #     '''各セクションのジオメトリ'''
    #     print('\n[ジオメトリ詳細]')
    #     print(f'  {'Index':<6} {'Name':<15} {'L (um)':<10} {'diam (um)':<12} {'nseg':<6}')
    #     print('  ' + '-' * 55)
        
    #     total_length = 0
    #     for i, node in enumerate(self._nodes):
    #         name = node.name()
    #         L = node.L
    #         diam = node.diam
    #         nseg = node.nseg
    #         total_length += L
            
    #         # 最初と最後、および途中のサンプルを表示
    #         if i < 3 or i >= len(self._nodes) - 3 or i == len(self._nodes) // 2:
    #             print(f'  {i:<6} {name:<15} {L:<10.3f} {diam:<12.3f} {nseg:<6}')
    #         elif i == 3:
    #             print(f'  {'...':<6} {'...':<15} {'...':<10} {'...':<12} {'...':<6}')
        
    #     print('  ' + '-' * 55)
    #     print(f'  総長さ（各L合計）: {total_length:.3f} um')
    
    # def print_connections(self):
    #     '''セクション接続の確認'''
    #     print('\n[接続状態]')
        
    #     connected_count = 0
    #     disconnected = []
        
    #     for i, node in enumerate(self._nodes):
    #         # 親セクションを確認
    #         parent_seg = node.parentseg()
            
    #         if i < 3 or i >= len(self._nodes) - 2:
    #             if parent_seg is not None:
    #                 parent_name = parent_seg.sec.name()
    #                 parent_pos = parent_seg.x
    #                 print(f'  node[{i}](0) <- {parent_name}({parent_pos})')
    #                 connected_count += 1
    #             else:
    #                 print(f'  node[{i}]: ルートセクション（親なし）')
    #                 if i != 0:
    #                     disconnected.append(i)
    #         elif i == 3:
    #             print(f'  ...')
    #         else:
    #             if parent_seg is not None:
    #                 connected_count += 1
    #             elif i != 0:
    #                 disconnected.append(i)
        
    #     print(f'\n  接続済みセクション: {connected_count}/{len(self._nodes)-1}')
        
    #     if disconnected:
    #         print(f'  ⚠ 未接続セクション: {disconnected}')
    #     else:
    #         print(f'  ✓ 全セクション正常に接続')
    
    # def print_mechanisms(self):
    #     '''挿入されているメカニズム'''
    #     print('\n[挿入メカニズム]')
        
    #     if len(self._nodes) > 0:
    #         node = self._nodes[0]
    #         mechanisms = []
            
    #         for mech in node.psection()['density_mechs'].keys():
    #             mechanisms.append(mech)
            
    #         print(f'  node[0]に挿入されたメカニズム ({len(mechanisms)}個):')
    #         for i, mech in enumerate(mechanisms):
    #             if i < 10 or i >= len(mechanisms) - 2:
    #                 print(f'    - {mech}')
    #             elif i == 10:
    #                 print(f'    ... ({len(mechanisms) - 12}個省略)')
            
    #         # 全ノードで同じメカニズムか確認
    #         all_same = True
    #         for node in self._nodes[1:]:
    #             node_mechs = set(node.psection()['density_mechs'].keys())
    #             if node_mechs != set(mechanisms):
    #                 all_same = False
    #                 break
            
    #         if all_same:
    #             print(f'  ✓ 全ノードで同一メカニズム')
    #         else:
    #             print(f'  ⚠ ノード間でメカニズムが異なる')
    
    # def print_coordinates(self):
    #     '''座標情報'''
    #     print('\n[座標情報]')
    #     coords = self._fiber.section_coord
        
    #     print(f'  座標数: {len(coords)}')
    #     print(f'  範囲: {coords[0]*1e6:.3f} um ~ {coords[len(coords)-1]*1e6:.3f} um')
    #     print(f'  （中心 = 0）')
        
    #     print('\n  サンプル座標:')
    #     for i in [0, 1, len(coords)//2, len(coords)-2, len(coords)-1]:
    #         if i < len(coords):
    #             print(f'    node[{i}]: {coords[i]*1e6:.3f} um')
    
    # def verify_integrity(self) -> bool:
    #     '''モデルの整合性を検証'''
    #     print('\n' + '=' * 60)
    #     print('整合性検証')
    #     print('=' * 60)
        
    #     errors = []
    #     warnings = []
        
    #     # 1. セグメント数の確認
    #     expected_n = int(self.length / self.dx)
    #     if self.n_segments != expected_n:
    #         warnings.append(f'セグメント数: 期待値{expected_n}, 実際{self.n_segments}')
        
    #     # 2. 総長さの確認
    #     total_L = sum(node.L for node in self._nodes)
    #     if abs(total_L - self.length) > 0.001:
    #         errors.append(f'総長さ不一致: 期待値{self.length}, 実際{total_L}')
        
    #     # 3. 接続の確認
    #     for i in range(1, len(self._nodes)):
    #         if self._nodes[i].parentseg() is None:
    #             errors.append(f'node[{i}]が未接続')
        
    #     # 4. 各セグメントの長さが均一か
    #     lengths = [node.L for node in self._nodes]
    #     if len(set(lengths)) > 1:
    #         warnings.append(f'セグメント長が不均一: {set(lengths)}')
        
    #     # 結果出力
    #     if errors:
    #         print('❌ エラー:')
    #         for e in errors:
    #             print(f'   - {e}')
        
    #     if warnings:
    #         print('⚠ 警告:')
    #         for w in warnings:
    #             print(f'   - {w}')
        
    #     if not errors and not warnings:
    #         print('✓ 全て正常')
        
    #     print('=' * 60)
        
    #     return len(errors) == 0
    
    # def visualize_structure(self, max_display: int = 50):
    #     '''構造を視覚的に表示'''
    #     print('\n[構造の視覚化]')
        
    #     n = min(self.n_segments, max_display)
    #     scale = max_display // self.n_segments if self.n_segments <= max_display else 1
        
    #     # 簡易図
    #     print('\n  セグメント配置:')
    #     print('  ', end='')
        
    #     if self.n_segments <= max_display:
    #         for i in range(self.n_segments):
    #             print('█', end='')
    #     else:
    #         displayed = 0
    #         for i in range(self.n_segments):
    #             if i < 10 or i >= self.n_segments - 10 or i == self.n_segments // 2:
    #                 print('█', end='')
    #                 displayed += 1
    #             elif i == 10:
    #                 print(f'...({self.n_segments - 21})...', end='')
        
    #     print()
    #     print(f'  |{'─' * (min(self.n_segments, 30))}|')
    #     print(f'  0 um{' ' * (min(self.n_segments, 30) - 10)}{self.length:.0f} um')



    # def print_detailed_connections(self):
    #     '''接続の詳細を調査'''
    #     print('\n[詳細接続デバッグ]')
    #     print('-' * 70)
        
    #     for i, node in enumerate(self._nodes):
    #         sec = node
            
    #         # このセクションの情報
    #         print(f'\nnode[{i}]: {sec.name()}')
            
    #         # 親セクション
    #         parent_seg = sec.parentseg()
    #         if parent_seg:
    #             print(f'  親: {parent_seg.sec.name()}({parent_seg.x})')
    #         else:
    #             print(f'  親: なし (ルートセクション)')
            
    #         # 子セクション
    #         children = sec.children()
    #         if children:
    #             print(f'  子: ', end='')
    #             for child in children:
    #                 # 接続位置を確認
    #                 child_ref = h.SectionRef(sec=child)
    #                 print(f'{child.name()}, ', end='')
    #             print()
    #         else:
    #             print(f'  子: なし')
            
    #         # 最初の数個と最後の数個だけ表示
    #         if i == 4:
    #             print(f'\n  ... (中略) ...')
    #         if i > 4 and i < len(self._nodes) - 3:
    #             continue
        
    #     # 接続の視覚化
    #     print('\n[接続チェーン]')
        
    #     # ルートセクションを見つける
    #     root = None
    #     for node in self._nodes:
    #         if node.parentseg() is None:
    #             root = node
    #             print(f'ルート発見: {node.name()}')
    #             break
        
    #     if root:
    #         # ルートから辿る
    #         print('\nルートからの接続チェーン:')
    #         current = root
    #         chain = [current.name()]
    #         visited = {current.name()}
            
    #         for _ in range(min(10, len(self._nodes))):
    #             children = list(current.children())
    #             if children:
    #                 next_sec = children[0]
    #                 if next_sec.name() not in visited:
    #                     chain.append(next_sec.name())
    #                     visited.add(next_sec.name())
    #                     current = next_sec
    #                 else:
    #                     break
    #             else:
    #                 break
            
    #         if len(chain) <= 10:
    #             print(' -> '.join(chain))
    #         else:
    #             print(' -> '.join(chain[:5]) + ' -> ... -> ' + chain[-1])


    # def verify_connection_direction(self):
    #     '''接続方向の検証'''
    #     print('\n[接続方向の検証]')
    #     print('-' * 70)
        
    #     correct_connections = 0
    #     incorrect_connections = []
        
    #     for i in range(len(self._nodes) - 1):
    #         node_i = self._nodes[i]
    #         node_i_plus_1 = self._nodes[i + 1]
            
    #         # node[i+1]の親がnode[i]であるべき
    #         parent = node_i_plus_1.parentseg()
            
    #         if parent is not None:
    #             parent_name = parent.sec.name()
    #             expected_parent_name = node_i.name()
    #             parent_pos = parent.x
                
    #             # 親が正しいか、接続位置が正しいか（1.0であるべき）
    #             if expected_parent_name in parent_name and abs(parent_pos - 1.0) < 0.01:
    #                 correct_connections += 1
    #             else:
    #                 incorrect_connections.append({
    #                     'child': f'node[{i+1}]',
    #                     'expected_parent': f'node[{i}](1)',
    #                     'actual_parent': f'{parent_name}({parent_pos})'
    #                 })
    #         else:
    #             incorrect_connections.append({
    #                 'child': f'node[{i+1}]',
    #                 'expected_parent': f'node[{i}](1)',
    #                 'actual_parent': 'なし'
    #             })
        
    #     print(f'正しい接続: {correct_connections}/{len(self._nodes)-1}')
        
    #     if incorrect_connections:
    #         print(f'\n不正な接続 ({len(incorrect_connections)}件):')
    #         for inc in incorrect_connections[:5]:
    #             print(f'  {inc['child']}: 期待={inc['expected_parent']}, 実際={inc['actual_parent']}')
    #         if len(incorrect_connections) > 5:
    #             print(f'  ... 他 {len(incorrect_connections)-5}件')
        
    #     return len(incorrect_connections) == 0