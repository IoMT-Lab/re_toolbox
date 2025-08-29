func0(std::vector<float, std::allocator<float> >, float):
endbr64
push   %rbp
mov    %rsp,%rbp
push   %rbx
sub    $0x28,%rsp
mov    %rdi,-0x28(%rbp)
movss  %xmm0,-0x2c(%rbp)
movl   $0x0,-0x18(%rbp)
mov    -0x18(%rbp),%eax
movslq %eax,%rbx
mov    -0x28(%rbp),%rax
mov    %rax,%rdi
callq  1cbc <_ZNKSt6vectorIfSaIfEE4sizeEv>
cmp    %rax,%rbx
setb   %al
test   %al,%al
je     12f8 <_Z5func0St6vectorIfSaIfEEf+0xcf>
mov    -0x18(%rbp),%eax
add    $0x1,%eax
mov    %eax,-0x14(%rbp)
mov    -0x14(%rbp),%eax
movslq %eax,%rbx
mov    -0x28(%rbp),%rax
mov    %rax,%rdi
callq  1cbc <_ZNKSt6vectorIfSaIfEE4sizeEv>
cmp    %rax,%rbx
setb   %al
test   %al,%al
je     12ef <_Z5func0St6vectorIfSaIfEEf+0xc6>
mov    -0x18(%rbp),%eax
movslq %eax,%rdx
mov    -0x28(%rbp),%rax
mov    %rdx,%rsi
mov    %rax,%rdi
callq  1ce4 <_ZNSt6vectorIfSaIfEEixEm>
movss  (%rax),%xmm2
movss  %xmm2,-0x30(%rbp)
mov    -0x14(%rbp),%eax
movslq %eax,%rdx
mov    -0x28(%rbp),%rax
mov    %rdx,%rsi
mov    %rax,%rdi
callq  1ce4 <_ZNSt6vectorIfSaIfEEixEm>
movss  (%rax),%xmm0
movss  -0x30(%rbp),%xmm2
subss  %xmm0,%xmm2
movaps %xmm2,%xmm0
callq  1c6d <_ZSt3absf>
movss  -0x2c(%rbp),%xmm1
comiss %xmm0,%xmm1
seta   %al
test   %al,%al
je     12e9 <_Z5func0St6vectorIfSaIfEEf+0xc0>
mov    $0x1,%eax
jmp    12fd <_Z5func0St6vectorIfSaIfEEf+0xd4>
addl   $0x1,-0x14(%rbp)
jmp    126f <_Z5func0St6vectorIfSaIfEEf+0x46>
addl   $0x1,-0x18(%rbp)
jmpq   1246 <_Z5func0St6vectorIfSaIfEEf+0x1d>
mov    $0x0,%eax
add    $0x28,%rsp
pop    %rbx
pop    %rbp
retq