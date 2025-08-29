use anyhow::anyhow;
use anyhow::Result;
use std::io::Read;
use std::path::PathBuf;
use std::{env, fs, io::Write as _, process::Command, str};
use tempfile;

#[derive(Debug, Copy, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum Subtype {
    LLM,
    RAG_exe_bench,
    RAG_mbpp,
}

#[derive(Debug, Copy, Clone, PartialEq, Eq, PartialOrd, Ord)]
enum Arch {
    ARM,
    X86_64,
}

pub fn list_functions(contents: &Vec<u8>) -> Result<Vec<String>> {
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;
    let arch = detect_arch(tfile.path().to_path_buf())?;

    let assembly = to_assembly(tfile.path().to_path_buf(), arch)?;
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(&assembly)?;

    let command_path = env::var("AI_DECOMP_PATH")?;
    let res = Command::new(command_path)
        .arg(tfile.path())
        .arg("list")
        .output()?;

    if let Some(0) = res.status.code() {
        let output = str::from_utf8(&res.stdout)?;
        Ok(output.split('\n').map(str::to_string).collect())
    } else {
        Ok(vec![])
    }
}

pub fn decompile_function(
    contents: &Vec<u8>,
    function_name: &str,
    subtype: Subtype,
) -> Result<Vec<u8>> {
    todo!()
}

pub fn decompile_all(contents: &Vec<u8>, subtype: Subtype) -> Result<Vec<u8>> {
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;
    let arch = detect_arch(tfile.path().to_path_buf())?;

    let assembly = to_assembly(tfile.path().to_path_buf(), arch)?;
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(&assembly)?;

    let tempdir = tempfile::tempdir()?;
    let output_path = tempdir.into_path().join("output.txt");
    let command_path = env::var("AI_DECOMP_PATH")?;
    let res = Command::new(command_path)
        .arg(tfile.path())
        .arg("decompile")
        .arg("-m")
        .arg("-d")
        .arg(if let Subtype::LLM = subtype {
            "general_llm"
        } else {
            "RAG"
        })
        .arg("--rag_db")
        .arg(if let Subtype::RAG_mbpp = subtype {
            "mbpp"
        } else {
            "exe_bench"
        })
        .arg("--output")
        .arg(&output_path)
        .output()?;

    if let Some(0) = res.status.code() {
        let mut f = fs::File::open(output_path)?;
        let mut output = Vec::new();
        f.read_to_end(&mut output)?;
        Ok(output)
    } else {
        println!("{:?}", res);
        Ok(vec![])
    }
}

fn detect_arch(filepath: PathBuf) -> Result<Arch> {
    let res = Command::new("readelf").arg("-h").arg(filepath).output()?;
    if let Some(0) = res.status.code() {
        let output = str::from_utf8(&res.stdout)?;
        let lines = output.split('\n');
        for line in lines {
            if line.contains("Machine:") {
                if line.contains("ARM") {
                    return Ok(Arch::ARM);
                } else {
                    return Ok(Arch::X86_64);
                }
            } else {
                continue;
            }
        }
    }

    Err(anyhow!("readelf failed"))
}

fn to_assembly(filepath: PathBuf, arch: Arch) -> Result<Vec<u8>> {
    let command = match arch {
        Arch::ARM => "arm-none-eabi-objdump",
        Arch::X86_64 => "objdump",
    };

    let res = Command::new(command).arg("-d").arg(filepath).output()?;
    if let Some(0) = res.status.code() {
        Ok(res.stdout)
    } else {
        Err(anyhow!("objdump failed"))
    }
}
