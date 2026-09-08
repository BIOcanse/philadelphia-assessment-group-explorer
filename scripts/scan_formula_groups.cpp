// Aggregate held-out predictions over original groups; deduplicate exact test extents.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <unordered_set>
#include <vector>
struct Group {uint64_t cl,ch,gl,gh;uint32_t n,low,equal,development,test,reserved;double sum,sq,development_sum,test_sum;};
static_assert(sizeof(Group)==88,"Original group schema changed");
template<class T> void read(std::ifstream& in,T* p,size_t n) {
    if(!in.read(reinterpret_cast<char*>(p),sizeof(T)*n))throw std::runtime_error("Truncated input");
}
struct Hash {
    size_t operator()(const std::vector<uint64_t>& words) const {
        uint64_t h=1469598103934665603ULL;
        for(uint64_t v:words){h^=v;h*=1099511628211ULL;h^=h>>32;}
        return size_t(h);
    }
};
struct Moments {
    uint64_t n=0;double y=0,y2=0,p=0,p2=0,yp=0,se=0,ae=0,bias=0,maximum=0;uint64_t worst=0;
    void add(double actual,double predicted,uint64_t id) {
        ++n;double dy=actual-y,dp=predicted-p;y+=dy/n;p+=dp/n;
        y2+=dy*(actual-y);p2+=dp*(predicted-p);yp+=dy*(predicted-p);
        double e=predicted-actual;se+=e*e;ae+=std::abs(e);bias+=e;
        if(std::abs(e)>maximum){maximum=std::abs(e);worst=id;}
    }
};
int main(int argc,char** argv) {
 try {
    if(argc!=4)throw std::runtime_error("profile weights, original catalog, output values required");
    std::ifstream input(argv[1],std::ios::binary),catalog(argv[2],std::ios::binary);std::ofstream output(argv[3],std::ios::binary);
    if(!input||!catalog||!output)throw std::runtime_error("Cannot open files");
    uint32_t hdr[5];read(input,hdr,5);
    if(hdr[0]!=0x46564c31)throw std::runtime_error("Wrong profile format");
    const size_t U=hdr[1],A=hdr[2],M=hdr[3],W=hdr[4],P=M+2;
    if(M>8||W!=(U+63)/64)throw std::runtime_error("Invalid dimensions");
    std::vector<uint64_t> atoms(A*W),extent(W);read(input,atoms.data(),atoms.size());
    std::vector<double> weights(U*P),sums(P);read(input,weights.data(),weights.size());
    std::unordered_set<std::vector<uint64_t>,Hash> observed;
    const unsigned limits[]={1,10,30,100,300};Moments stats[2][5][8];
    uint64_t index=0,nonbaseline=0,empty=0,unique=0,selected=0,mismatches=0;double max_sum_error=0;
    Group g;
    while(catalog.read(reinterpret_cast<char*>(&g),sizeof(g))) {
        std::fill(extent.begin(),extent.end(),~uint64_t(0));
        if(U%64)extent.back()=(uint64_t(1)<<(U%64))-1;
        uint64_t masks[2]={g.gl,g.gh};
        for(int half=0;half<2;++half){uint64_t mask=masks[half];
            while(mask){size_t a=64*half+__builtin_ctzll(mask);mask&=mask-1;
                if(a>=A)throw std::runtime_error("Invalid atom");
                for(size_t w=0;w<W;++w)extent[w]&=atoms[a*W+w];
            }
        }
        std::fill(sums.begin(),sums.end(),0.);
        for(size_t w=0;w<W;++w){uint64_t bits=extent[w];
            while(bits){size_t u=w*64+__builtin_ctzll(bits);bits&=bits-1;
                for(size_t m=0;m<P;++m)sums[m]+=weights[u*P+m];
            }
        }
        if(sums[0]!=g.test)++mismatches;
        max_sum_error=std::max(max_sum_error,std::abs(sums[1]-g.test_sum));
        if(g.cl||g.ch){
            ++nonbaseline;
            if(!g.test)++empty;
            else {
                bool fresh=observed.insert(extent).second;unique+=fresh;
                double actual=sums[1]/sums[0];
                for(int t=0;t<5;++t)if(g.test>=limits[t])for(size_t m=0;m<M;++m){
                    double predicted=sums[m+2]/sums[0];
                    stats[0][t][m].add(actual,predicted,index);
                    if(fresh)stats[1][t][m].add(actual,predicted,index);
                }
                if(fresh&&g.test>=30){
                    double prefix[3]={double(index),double(g.test),actual};output.write(reinterpret_cast<char*>(prefix),sizeof(prefix));
                    for(size_t m=0;m<M;++m){double predicted=sums[m+2]/sums[0];output.write(reinterpret_cast<char*>(&predicted),8);}
                    ++selected;
                }
            }
        }
        ++index;
    }
    if(!catalog.eof()||!output)throw std::runtime_error("Input/output failure");
    std::cout<<std::setprecision(17)<<"{\"scanned\":"<<index<<",\"canonical_groups\":"<<nonbaseline
        <<",\"empty_test_groups\":"<<empty<<",\"unique_test_member_groups\":"<<unique<<",\"saved_unique_n30\":"<<selected
        <<",\"count_mismatches\":"<<mismatches<<",\"maximum_ratio_sum_error\":"<<max_sum_error<<",\"metrics\":[";
    bool first=true;
    for(int b=0;b<2;++b)for(int t=0;t<5;++t)for(size_t m=0;m<M;++m){
        const auto& a=stats[b][t][m];if(!first)std::cout<<",";first=false;
        double vy=std::max(0.,a.y2),vp=std::max(0.,a.p2);
        std::cout<<"{\"basis\":\""<<(b?"unique_test_members":"canonical_groups")<<"\",\"minimum_n\":"<<limits[t]
            <<",\"method_index\":"<<m<<",\"groups\":"<<a.n<<",\"r\":";
        if(vy>1e-24*a.n&&vp>1e-24*a.n)std::cout<<a.yp/std::sqrt(vy*vp);else std::cout<<"null";
        std::cout<<",\"r2\":";if(vy>1e-24*a.n)std::cout<<1-a.se/vy;else std::cout<<"null";
        std::cout<<",\"rmse_pp\":";if(a.n)std::cout<<100*std::sqrt(a.se/a.n);else std::cout<<"null";
        std::cout<<",\"mae_pp\":";if(a.n)std::cout<<100*a.ae/a.n;else std::cout<<"null";
        std::cout<<",\"baseline_skill\":";if(stats[b][t][0].se>1e-24)std::cout<<1-a.se/stats[b][t][0].se;else std::cout<<"null";
        std::cout<<",\"max_abs_pp\":"<<100*a.maximum<<",\"worst_id\":"<<a.worst<<"}";
    }
    std::cout<<"]}"<<std::endl;
    return mismatches||max_sum_error>1e-8?2:0;
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}
