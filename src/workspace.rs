use crate::Compiler;
use crate::Decompiler;
use crate::Format;
use std::fs::File;
use std::io::Read;
use std::path::PathBuf;

#[derive(Debug)]
pub struct Workspace {
    pub decompiler: Decompiler,
    pub compiler: Compiler,

    pub active_file: Option<Workfile>,
}

impl Workspace {
    pub fn new() -> Self {
        Self {
            decompiler: Decompiler::Ghidra,
            compiler: Compiler::Gcc,
            active_file: None,
        }
    }
}

#[derive(Debug)]
pub struct Workfile {
    pub filename: String,
    pub format: Format,
    pub contents: Vec<u8>,
    pub loaded_from: PathBuf,
    pub last_saved: PathBuf,
    pub modified_since_load: bool,
    pub modified_since_last_save: bool,
}

impl Workfile {
    pub fn new(path: PathBuf, format: Format) -> std::io::Result<Self> {
        let mut f = File::open(&path)?;
        let mut contents = Vec::new();
        f.read_to_end(&mut contents)?;

        let filename = path.file_stem().unwrap();
        Ok(Self {
            filename: filename.to_str().unwrap().to_string(),
            format,
            contents,
            loaded_from: path.clone(),
            last_saved: path,
            modified_since_load: false,
            modified_since_last_save: false,
        })
    }
}
