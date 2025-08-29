use std::fmt::Display;

use anyhow::{anyhow, Result};
use clap::{Args, Subcommand, ValueEnum};

use crate::{Format, Workspace};

pub mod angr;
pub mod ghidra;
pub mod llm;

#[derive(Subcommand, Debug)]
pub enum DecompilerSubcommand {
    /// Display currently configured decompiler
    Get,

    /// Set current decompiler
    Set(DecompilerSetArgs),

    /// List available decompilers
    List,

    /// List functions present in binary, using current decompiler
    ListFunctions,

    /// Decompile function, using current decompiler
    Decompile(DecompileArgs),
}

#[derive(Args, Debug)]
pub struct DecompilerSetArgs {
    /// Decompiler to switch to
    decompiler: Decompiler,
}

#[derive(Debug, Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum)]
pub enum Decompiler {
    Ghidra,
    Angr,
    LLM,
    RAG_exe_bench,
    RAG_mbpp,
}

impl Display for Decompiler {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{}",
            match self {
                Self::Angr => "Angr",
                Self::Ghidra => "Ghidra",
                Self::LLM => "LLM",
                Self::RAG_exe_bench => "RAG - exe_bench",
                Self::RAG_mbpp => "RAG - mbpp",
            }
        )?;
        Ok(())
    }
}

#[derive(Args, Debug)]
pub struct DecompileArgs {
    /// Function to decompile
    function: Option<String>,
}

impl DecompilerSubcommand {
    pub fn execute(&self, workspace: &mut Workspace) {
        match self {
            DecompilerSubcommand::Get => {
                println!("Current decompiler {}", workspace.decompiler);
            }
            DecompilerSubcommand::Set(decompiler_set_args) => {
                workspace.decompiler = decompiler_set_args.decompiler;
                println!("Decompiler changed to {}", decompiler_set_args.decompiler);
            }
            DecompilerSubcommand::List => {
                println!("Available decompilers: ");
                println!("  {}", Decompiler::Angr);
                println!("  {}", Decompiler::Ghidra);
            }
            DecompilerSubcommand::ListFunctions => {
                if let Some(workfile) = &workspace.active_file {
                    match workfile.format {
                        Format::Bytecode => {
                            println!("Running list_function from {}...", workspace.decompiler);

                            let function_names = match workspace.decompiler {
                                Decompiler::Ghidra => ghidra::list_functions(&workfile.contents),
                                Decompiler::Angr => angr::list_functions(&workfile.contents),
                                Decompiler::LLM
                                | Decompiler::RAG_exe_bench
                                | Decompiler::RAG_mbpp => llm::list_functions(&workfile.contents),
                            };

                            if let Ok(functions) = function_names {
                                for function in functions {
                                    println!("  {}", function);
                                }
                            } else {
                                println!("!! Unexpected error occurred !!");
                            }
                        }
                        Format::Source => {
                            println!("!! Decompiler cannot be used on Source file !!")
                        }
                    }
                } else {
                    println!("! No active file to decompile !");
                }
            }
            DecompilerSubcommand::Decompile(decompile_args) => {
                if let Some(workfile) = &mut workspace.active_file {
                    match workfile.format {
                        Format::Bytecode => {
                            let decomp = match &decompile_args.function {
                                Some(function) => {
                                    println!(
                                        "Decompiling function {} with {}... ",
                                        function, workspace.decompiler
                                    );
                                    match workspace.decompiler {
                                        Decompiler::Ghidra => ghidra::decompile_function(
                                            &workfile.contents,
                                            &function,
                                        ),
                                        Decompiler::Angr => {
                                            println!("!! Decompiling with Angr is not currently supported !!");
                                            Err(anyhow!("bad"))
                                        }
                                        Decompiler::LLM => llm::decompile_function(
                                            &workfile.contents,
                                            &function,
                                            llm::Subtype::LLM,
                                        ),
                                        Decompiler::RAG_exe_bench => llm::decompile_function(
                                            &workfile.contents,
                                            &function,
                                            llm::Subtype::RAG_exe_bench,
                                        ),
                                        Decompiler::RAG_mbpp => llm::decompile_function(
                                            &workfile.contents,
                                            &function,
                                            llm::Subtype::RAG_mbpp,
                                        ),
                                    }
                                }
                                None => {
                                    println!(
                                        "Decompiling whole file with {}...",
                                        workspace.decompiler
                                    );
                                    match workspace.decompiler {
                                        Decompiler::Ghidra => {
                                            ghidra::decompile_all(&workfile.contents)
                                        }
                                        Decompiler::Angr => {
                                            println!("!! Decompiling with Angr is not currently supported !!");
                                            Err(anyhow!("bad"))
                                        }
                                        Decompiler::LLM => llm::decompile_all(
                                            &workfile.contents,
                                            llm::Subtype::LLM,
                                        ),
                                        Decompiler::RAG_exe_bench => llm::decompile_all(
                                            &workfile.contents,
                                            llm::Subtype::RAG_exe_bench,
                                        ),
                                        Decompiler::RAG_mbpp => llm::decompile_all(
                                            &workfile.contents,
                                            llm::Subtype::RAG_mbpp,
                                        ),
                                    }
                                }
                            };

                            if let Ok(source) = decomp {
                                println!("... Function decompiled");
                                println!("Replacing working file with new content");

                                workfile.format = Format::Source;
                                workfile.contents = source;
                                workfile.modified_since_load = true;
                                workfile.modified_since_last_save = true;
                            } else {
                                println!("!! Unexpected error occurred !!");
                            }
                        }
                        Format::Source => {
                            println!("!! Decompiler cannot be used on Source file !!")
                        }
                    }
                } else {
                    println!("! No active file to decompile !");
                }
            }
        }
    }
}
