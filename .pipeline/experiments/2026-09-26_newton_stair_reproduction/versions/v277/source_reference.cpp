// Compile the frozen v271 source kernel unchanged under isolated symbols.
#define reactive_stair source_reference271
#include "v271/src/plan_env/src/source_surface_geometry.cpp"
#undef reactive_stair
extern "C" void *source271Create(const char *tri,const char *meta,const char *tf,const char *mf){return new source_reference271::source_surface::Field(tri,meta,tf,mf);}
extern "C" void source271Destroy(void *p){delete static_cast<source_reference271::source_surface::Field*>(p);}
extern "C" void source271Query(void *p,double x,double y,double z,double yaw,double *out){
 auto *field=static_cast<source_reference271::source_surface::Field*>(p);
 source_reference271::source_surface::V witness={{0.,0.,0.}};
 out[0]=field->assess(x,y,z-.3,yaw,&witness);for(int i=1;i<5;++i)out[i]=0.;
 for(int i=0;i<3;++i)out[5+i]=witness[i];
 if(out[0]<.15)for(int k=0;k<4;++k){std::array<double,4>a{{x,y,z,yaw}},b=a;a[k]+=1e-5;b[k]-=1e-5;
  out[k+1]=(field->assess(a[0],a[1],a[2]-.3,a[3])-field->assess(b[0],b[1],b[2]-.3,b[3]))/(2e-5);
 }
}
