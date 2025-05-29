use std::{env, fs, io::Write as _, process::Command, str};
use std::path::PathBuf;
use anyhow::Result;
use tempfile;

pub fn list_functions(contents: &Vec<u8>) -> Result<Vec<String>> {
    let tdir = tempfile::tempdir()?;
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;

    let ghidra_dir = env::var("GHIDRA_DIR")?;
    let command_path = ghidra_dir.clone() + "/ghidra_11.2.1_PUBLIC/support/analyzeHeadless";
    let script_path = ghidra_dir.clone() + "/ghidra_11.2.1_PUBLIC/Ghidra/Features/Base/ghidra_scripts";
    let local_script_path = ghidra_dir.clone() + "/scripts";

    let res = Command::new(command_path)
        .arg(tdir.path())
        .arg("project")
        .arg("-import")
        .arg(tfile.path())
        .arg("-scriptPath")
        .arg(script_path)
        .arg("-scriptPath")
        .arg(local_script_path)
        .arg("-postScript")
        .arg("ListFunctionsH.java")
        .arg("deleteProject")
        .output()?;

    if let Some(0) = res.status.code() {
        let output = str::from_utf8(&res.stdout)?;
        let lines = output.split('\n');

        let functions = lines
            .filter(|s| s.starts_with("INFO  ListFunctionsH.java>"))
            .map(|s| s.trim_start_matches("INFO  ListFunctionsH.java> "))
            .map(|s| s.trim_end_matches(" (GhidraScript)  "))
            .map(|s| s.to_owned())
            .collect::<Vec<String>>();
        Ok(functions)
    } else {
        Ok(vec![])
    }
    
}

pub fn decompile_function(contents: &Vec<u8>, function_name: &str) -> Result<Vec<u8>> {
    let tdir = tempfile::tempdir()?;
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;

    let ghidra_dir = env::var("GHIDRA_DIR")?;
    let command_path = ghidra_dir.clone() + "/ghidra_11.2.1_PUBLIC/support/analyzeHeadless";
    let script_path = ghidra_dir.clone() + "/ghidra_11.2.1_PUBLIC/Ghidra/Features/Base/ghidra_scripts";
    let local_script_path = ghidra_dir.clone() + "/scripts";

    let res = Command::new(command_path)
        .arg(tdir.path())
        .arg("project")
        .arg("-import")
        .arg(tfile.path())
        .arg("-scriptPath")
        .arg(script_path)
        .arg("-scriptPath")
        .arg(local_script_path)
        .arg("-postScript")
        .arg("DecompileFunctionH.java")
        .arg(function_name)
        .arg("deleteProject")
        .output()?;

        let mut func = Vec::new();
        if let Some(0) = res.status.code() {
            let output = str::from_utf8(&res.stdout)?;
            let lines = output.split('\n');
            
            let mut in_decomp = false;
            for line in lines {
                if line.starts_with("INFO  DecompileFunctionH.java>") {
                    in_decomp = true;
                } else if line.contains("(GhidraScript)") {
                    break;
                } else if in_decomp {
                    func.extend(line.as_bytes());
                    func.push(b'\n');
                }
                
            }

        } 
        Ok(func)

}




pub fn run_struct_rebuilder(contents: &Vec<u8>) -> Result<()> {
    let tdir = tempfile::tempdir()?;
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;


    let ghidra_dir = env::var("GHIDRA_DIR")?;
    let command_path = ghidra_dir.clone() + "/ghidra_11.2.1_PUBLIC/support/analyzeHeadless";

    let script_path = ghidra_dir.clone() + "/ghidra_11.2.1_PUBLIC/Ghidra/Features/Base/ghidra_scripts";
    let local_script_path = ghidra_dir.clone() + "/scripts";

    let mut cmd = Command::new(command_path);
    cmd.arg(tdir.path())
        .arg("project")
        .arg("-import")
        .arg(tfile.path())
        .arg("-scriptPath")
        .arg(script_path)
        .arg("-scriptPath")
        .arg(local_script_path)
        .arg("-postScript")
        .arg("StructRebuilderEntry.java")
        .arg("deleteProject");

    let res = cmd.output()?;

    if !res.status.success() {
        eprintln!("stderr: {}", String::from_utf8_lossy(&res.stderr));
    }

    let plugin_path = env::var("PLUGIN_PATH")
        .map(PathBuf::from)
        .map_err(|_| std::io::Error::new(std::io::ErrorKind::NotFound, "PLUGIN_PATH is not set"))?;

    let script_path = plugin_path
        .parent() // plugins/
        .map(|p| p.join("tools/AccessPatternGraph/GraphAnalyzer.py"))
        .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::NotFound, "Failed to resolve script path"))?;


    let output = Command::new("python3")
        .arg(&script_path)
        .output()?;

    if !output.status.success() {
        eprintln!("stderr: {}", String::from_utf8_lossy(&output.stderr));
    }
    Ok(())
}


pub fn stack_struct_rebuild(contents: &Vec<u8>, func_name: &str) ->Result<Vec<u8>> {

    let tdir = tempfile::tempdir()?;
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;


    let ghidra_dir = env::var("GHIDRA_DIR")?;
    let command_path = ghidra_dir.clone() + "/ghidra_11.2.1_PUBLIC/support/analyzeHeadless";

    let script_path = ghidra_dir.clone() + "/ghidra_11.2.1_PUBLIC/Ghidra/Features/Base/ghidra_scripts";
    let local_script_path = ghidra_dir.clone() + "/scripts";

    let mut cmd = Command::new(command_path);
    cmd.arg(tdir.path())
        .arg("project")
        .arg("-import")
        .arg(tfile.path())
        .arg("-scriptPath")
        .arg(script_path)
        .arg("-scriptPath")
        .arg(local_script_path)
        .arg("-postScript")
        .arg("StructRebuilderEntry.java")
        .arg("deleteProject");

    let res = cmd.output()?;
    if !res.status.success() {
        eprintln!("stderr: {}", String::from_utf8_lossy(&res.stderr));
    }
    if let Some(0) = res.status.code() {
        let output_path = PathBuf::from("/tmp/decompiled_result/").join(format!("{}.txt", func_name));
        let func_bytes = fs::read(output_path)?;
        return Ok(func_bytes);
    }

    Err("Not such function").expect("error")

}