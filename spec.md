**项目技术规格：自动化3D模型重构守护进程（2025修正版）**

#### 1\. 总体目标

构建一个支持中文文件名、自动自适应网格数量、可配置的后台服务。服务以单线程、顺序化的方式处理任务，监控指定目录，对新加入的 `.zip` 文件执行解压、格式转换、Remesh、再转换、压缩的全套流程，并将最终成品存放到输出目录。所有流程和参数均自动化，无需人工干预。

#### 2\. 核心处理逻辑 (`main.py`)

- **启动流程**:
    1. 加载 `config.yaml` 配置文件。
    2. 初始化日志记录器。
    3. 连接到 `db/database.py` 定义的SQLite数据库。
    4. 启动时调用 `cleanup.py` 的 `cleanup_stale_tasks()`，将所有PROCESSING任务重置为FAILED，保证断电恢复安全。

- **任务发现与主循环**:
    1. `watchdog` 监控 `in_zips` 目录，发现新zip后写入数据库，状态为PENDING。
    2. 主循环不断从数据库拉取PENDING任务，状态置为PROCESSING，调用 `pipeline.py` 的 `process_task(task)`。
    3. `process_task` 成功则状态置为DONE，失败则FAILED，均调用 `cleanup.py` 的 `cleanup_workdir(uuid)` 清理临时目录。
    4. 无任务时 sleep 5 秒。

#### 3\. 任务处理管道 (`pipeline.py`)

- **输入**: 任务对象（含UUID、zip路径等）
- **输出**: 无。成功时正常返回，失败时抛出异常。
- **流程**:
    1. 创建以UUID命名的工作目录。
    2. 解压zip到工作目录，支持中文文件名。
    3. 查找所有 `.obj` 文件，支持多模型批量处理。
    4. 对每个OBJ：
        - 转FBX（`converter.py`，调用Blender无头模式，支持中文路径）
        - Remesh（`remesher.py`，调用xremesh.exe，参数自动自适应）
            - **TargetQuadCount**：自动统计FBX三角面数，取其1/4
            - **CurvatureAdaptivness**：20
            - **ExactQuadCount**：1
            - **UseVertexColorMap**：0
            - **UseMaterialIds**：0
            - **UseIndexedNormals**：0
            - **AutoDetectHardEdges**：0
            - 其它参数均可在 `config.yaml` 配置
            - Remesh参数写入settings文件，调用xremesh.exe
        - Remesh后FBX转回OBJ（`converter.py`，Blender无头模式）
    5. 结果OBJ文件名自动还原为原始中文名。
    6. 只打包blenderobj目录下所有文件为zip，输出到out_zips。
    7. **无论任务成功或失败，均自动清理wip目录下的临时工作目录。**

#### 4\. Remesh参数与自适应逻辑 (`remesher.py`)

- 采用Blender无头模式统计FBX三角面数，保证兼容性和准确性。
- TargetQuadCount=三角面数*0.25，自动写入settings。
- 其它参数均按需求写死或可配置。
- Remesh失败自动抛出异常，主流程捕获并记录。

#### 5\. 中文与ASCII映射 (`utils/chinese_ascii.py`)

- 支持OBJ/FBX/MTL等文件的中文名与ASCII名互转，保证跨平台兼容和最终输出中文名还原。

#### 6\. 配置文件 (`config.yaml`)

- 路径、xremesh/blender可执行文件、数据库等均可配置。
- 示例：
```yaml
paths:
  input_dir: "test/in_zips"
  output_dir: "test/out_zips"
  work_dir: "test/wip"
  database_file: "test/db/tasks.sqlite"
  xremesh_executable: "vendor/QuadRemesher/EngineWin/xremesh.exe"
  blender_executable: "vendor/blender-4.5.3-windows-x64/blender.exe"

main_loop:
  sleep_interval_seconds: 5
```

#### 7\. 其它细节

- 所有流程日志详细，异常自动记录。
- 任务失败不会影响其它任务，批量处理健壮。
- 代码结构清晰，易于维护和扩展。
- 完全自动化，无需人工干预，适合大批量模型处理场景。
