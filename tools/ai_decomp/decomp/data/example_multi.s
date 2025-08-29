func1(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >):
endbr64
push   %rbp
mov    %rsp,%rbp
push   %rbx
sub    $0x58,%rsp
mov    %rdi,-0x58(%rbp)
mov    %rsi,-0x60(%rbp)
mov    %fs:0x28,%rax
mov    %rax,-0x18(%rbp)
xor    %eax,%eax
mov    -0x58(%rbp),%rax
mov    %rax,%rdi
callq  34f6 <_ZNSt6vectorINSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEESaIS5_EEC1Ev>
lea    -0x40(%rbp),%rax
mov    %rax,%rdi
callq  23f0 <_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEC1Ev@plt>
movl   $0x0,-0x48(%rbp)
movl   $0x0,-0x44(%rbp)
mov    -0x44(%rbp),%eax
movslq %eax,%rbx
mov    -0x60(%rbp),%rax
mov    %rax,%rdi
callq  2410 <_ZNKSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE6lengthEv@plt>
cmp    %rax,%rbx
setb   %al
test   %al,%al
je     265b <_Z5func0NSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE+0xf2>
mov    -0x44(%rbp),%eax
movslq %eax,%rdx
mov    -0x60(%rbp),%rax
mov    %rdx,%rsi
mov    %rax,%rdi
callq  2470 <_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEixEm@plt>
movzbl (%rax),%eax
mov    %al,-0x49(%rbp)
cmpb   $0x28,-0x49(%rbp)
jne    260a <_Z5func0NSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE+0xa1>
addl   $0x1,-0x48(%rbp)
movsbl -0x49(%rbp),%edx
lea    -0x40(%rbp),%rax
mov    %edx,%esi
mov    %rax,%rdi
callq  22e0 <_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEpLEc@plt>
cmpb   $0x29,-0x49(%rbp)
jne    2652 <_Z5func0NSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE+0xe9>
subl   $0x1,-0x48(%rbp)
movsbl -0x49(%rbp),%edx
lea    -0x40(%rbp),%rax
mov    %edx,%esi
mov    %rax,%rdi
callq  22e0 <_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEpLEc@plt>
cmpl   $0x0,-0x48(%rbp)
jne    2652 <_Z5func0NSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE+0xe9>
lea    -0x40(%rbp),%rdx
mov    -0x58(%rbp),%rax
mov    %rdx,%rsi
mov    %rax,%rdi
callq  36dc <_ZNSt6vectorINSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEESaIS5_EE9push_backERKS5_>
lea    -0x40(%rbp),%rax
lea    0x29c2(%rip),%rsi
mov    %rax,%rdi
callq  23e0 <_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEaSEPKc@plt>
addl   $0x1,-0x44(%rbp)
jmpq   25b3 <_Z5func0NSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE+0x4a>
lea    -0x40(%rbp),%rax
mov    %rax,%rdi
callq  22d0 <_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEED1Ev@plt>
mov    -0x18(%rbp),%rax
xor    %fs:0x28,%rax
je     26a9 <_Z5func0NSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE+0x140>
jmp    26a4 <_Z5func0NSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE+0x13b>
endbr64
mov    %rax,%rbx
lea    -0x40(%rbp),%rax
mov    %rax,%rdi
callq  22d0 <_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEED1Ev@plt>
mov    -0x58(%rbp),%rax
mov    %rax,%rdi
callq  3694 <_ZNSt6vectorINSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEESaIS5_EED1Ev>
mov    %rbx,%rax
mov    %rax,%rdi
callq  2430 <_Unwind_Resume@plt>
callq  23b0 <__stack_chk_fail@plt>
mov    -0x58(%rbp),%rax
add    $0x58,%rsp
pop    %rbx
pop    %rbp
retq

func2(float):
endbr64
push   %rbp
mov    %rsp,%rbp
movss  %xmm0,-0x4(%rbp)
movss  -0x4(%rbp),%xmm0
cvttss2si %xmm0,%eax
cvtsi2ss %eax,%xmm1
movss  -0x4(%rbp),%xmm0
subss  %xmm1,%xmm0
pop    %rbp
retq

func3(std::vector<float, std::allocator<float> >, float):
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